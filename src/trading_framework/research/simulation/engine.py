"""Bar-sequential Strategy Research simulation engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.profiling import optional_phase
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.research.simulation.assumptions import SimulationAssumptions
from trading_framework.research.simulation.compile import (
    compile_simulation_input,
    compile_simulation_input_from_columnar,
)
from trading_framework.research.simulation.facts import (
    SimulatedTrade,
    equity_points_to_dataframe,
    simulated_trades_to_dataframe,
)
from trading_framework.research.simulation.input import CompiledSimulationInput
from trading_framework.research.simulation.kernels.bracket import (
    materialize_bracket_kernel_equity,
    materialize_bracket_kernel_trades,
    run_bracket_kernel,
)
from trading_framework.research.simulation.kernels.fixed_bars import (
    materialize_kernel_equity,
    materialize_kernel_trades,
    run_fixed_bars_kernel,
)
from trading_framework.research.simulation.kernels.reference import (
    _observed_at_index_by_ns,
    _open_position_counts_by_bar_index,
)
from trading_framework.strategy.exit_model import FixedBarsExitModel, PriceBracketExit
from trading_framework.strategy.risk_model import RiskModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition


class SimulationEngineError(ValidationError):
    """Raised when bar-sequential simulation inputs are invalid."""


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Outcome of one bar-sequential simulation pass."""

    trades: pl.DataFrame
    equity: pl.DataFrame


class BarSequentialSimulator:
    """Simulate one strategy on ordered OHLCV bars with explicit fill assumptions."""

    def simulate(
        self,
        *,
        bars: Sequence[MarketBar],
        entry_signals: pl.DataFrame,
        strategy_model: StrategyModelDefinition,
        assumptions: SimulationAssumptions,
        instrument: str,
        source_dataset_ref: str,
    ) -> SimulationResult:
        ordered_bars = tuple(bars)
        if not ordered_bars:
            return SimulationResult(
                trades=simulated_trades_to_dataframe([]),
                equity=equity_points_to_dataframe([]),
            )
        _validate_entry_signals(entry_signals)
        exit_model = _dispatch_exit_model(strategy_model)
        risk_model = _require_structural_risk_model(strategy_model)
        with optional_phase("simulate.compile_input"):
            compiled = compile_simulation_input(
                bars=ordered_bars,
                entry_signals=entry_signals,
            )
        quantity = risk_model.position_quantity()
        return _run_dispatched_kernel(
            exit_model=exit_model,
            compiled=compiled,
            quantity=quantity,
            assumptions=assumptions,
            strategy_model_id=strategy_model.strategy_model_id,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
        )

    def simulate_from_columnar(
        self,
        *,
        column_batch: OhlcvColumnBatch,
        entry_signals: pl.DataFrame,
        strategy_model: StrategyModelDefinition,
        assumptions: SimulationAssumptions,
        instrument: str,
        source_dataset_ref: str,
    ) -> SimulationResult:
        """Simulate one strategy from columnar OHLCV without ``MarketBar`` materialization."""
        if not column_batch.timestamps:
            return SimulationResult(
                trades=simulated_trades_to_dataframe([]),
                equity=equity_points_to_dataframe([]),
            )
        _validate_entry_signals(entry_signals)
        exit_model = _dispatch_exit_model(strategy_model)
        risk_model = _require_structural_risk_model(strategy_model)
        with optional_phase("simulate.compile_input"):
            compiled = compile_simulation_input_from_columnar(
                column_batch=column_batch,
                entry_signals=entry_signals,
            )
        quantity = risk_model.position_quantity()
        return _run_dispatched_kernel(
            exit_model=exit_model,
            compiled=compiled,
            quantity=quantity,
            assumptions=assumptions,
            strategy_model_id=strategy_model.strategy_model_id,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
        )


def _validate_entry_signals(entry_signals: pl.DataFrame) -> None:
    required = {"available_at", "direction"}
    missing = required.difference(entry_signals.columns)
    if missing:
        msg = f"entry_signals missing required columns: {sorted(missing)}"
        raise SimulationEngineError(msg)


def _dispatch_exit_model(
    strategy_model: StrategyModelDefinition,
) -> FixedBarsExitModel | PriceBracketExit:
    """Dispatch ``strategy_model.exit_model`` to the kernel it can run on.

    Two shapes are supported: ``FixedBarsExitModel`` dispatches to the
    existing ``kernels/fixed_bars.py`` kernel, unchanged; any exit model
    structurally conformant with ``PriceBracketExit`` dispatches to
    ``kernels/bracket.py`` (``kernels/bracket.py`` is not edited by this
    dispatch - only called). Anything that is neither is refused here, with
    the same ``SimulationEngineError`` ``BarSequentialSimulator`` has always
    raised for an unsupported exit model, its wording widened to describe
    both supported shapes rather than naming one class. This function is the
    single dispatch point for both ``simulate()`` and
    ``simulate_from_columnar()``; the actual kernel call is factored into
    ``_run_dispatched_kernel`` so neither call site duplicates the branch.
    """
    exit_model = strategy_model.exit_model
    if isinstance(exit_model, FixedBarsExitModel | PriceBracketExit):
        return exit_model
    msg = (
        "BarSequentialSimulator supports FixedBarsExitModel or a "
        "PriceBracketExit-conformant exit model only"
    )
    raise SimulationEngineError(msg)


def _require_structural_risk_model(strategy_model: StrategyModelDefinition) -> RiskModel:
    """Accept any ``RiskModel`` structurally; the engine only calls ``position_quantity()``."""
    risk_model: object = strategy_model.risk_model
    if not isinstance(risk_model, RiskModel):
        msg = (
            "BarSequentialSimulator requires a RiskModel exposing "
            "position_quantity() and allows_new_entry()"
        )
        raise SimulationEngineError(msg)
    return risk_model


def _run_dispatched_kernel(
    *,
    exit_model: FixedBarsExitModel | PriceBracketExit,
    compiled: CompiledSimulationInput,
    quantity: Decimal,
    assumptions: SimulationAssumptions,
    strategy_model_id: str,
    instrument: str,
    source_dataset_ref: str,
) -> SimulationResult:
    """Run and materialize the kernel matching ``exit_model``'s dispatched shape.

    Shared by ``simulate()`` and ``simulate_from_columnar()`` so the
    fixed-bars/bracket branch is written once, not duplicated per call site.
    """
    if isinstance(exit_model, PriceBracketExit):
        with optional_phase("simulate.run_kernel"):
            bracket_kernel_result = run_bracket_kernel(
                compiled,
                stop_loss_bps=exit_model.stop_loss_bps,
                take_profit_bps=exit_model.take_profit_bps,
                max_bars=exit_model.max_bars,
                quantity=float(quantity),
                slippage_bps=float(assumptions.slippage_bps),
                commission_per_side=float(assumptions.commission_per_side),
                initial_capital=float(assumptions.initial_capital),
            )
        with optional_phase("simulate.materialize_results"):
            trades = materialize_bracket_kernel_trades(
                bracket_kernel_result,
                strategy_model_id=strategy_model_id,
                instrument=instrument,
                source_dataset_ref=source_dataset_ref,
                quantity=quantity,
            )
            equity = materialize_bracket_kernel_equity(
                bracket_kernel_result,
                compiled.bars.observed_at_ns,
            )
        return SimulationResult(
            trades=simulated_trades_to_dataframe(trades),
            equity=equity_points_to_dataframe(equity),
        )

    with optional_phase("simulate.run_kernel"):
        fixed_bars_kernel_result = run_fixed_bars_kernel(
            compiled,
            exit_after_bars=exit_model.exit_after_bars,
            quantity=float(quantity),
            slippage_bps=float(assumptions.slippage_bps),
            commission_per_side=float(assumptions.commission_per_side),
            initial_capital=float(assumptions.initial_capital),
        )
    with optional_phase("simulate.materialize_results"):
        trades = materialize_kernel_trades(
            fixed_bars_kernel_result,
            strategy_model_id=strategy_model_id,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
            exit_reason=exit_model.default_exit_reason,
            quantity=quantity,
        )
        equity = materialize_kernel_equity(
            fixed_bars_kernel_result,
            compiled.bars.observed_at_ns,
        )
    return SimulationResult(
        trades=simulated_trades_to_dataframe(trades),
        equity=equity_points_to_dataframe(equity),
    )


# Backward-compatible helpers retained for unit tests.
def _build_bar_timestamp_index(bars: Sequence[MarketBar]) -> _LegacyBarTimestampIndex:
    observed_at_to_index: dict[datetime, int] = {}
    available_at_to_index: dict[datetime, int] = {}
    for index, bar in enumerate(bars):
        observed_at_to_index.setdefault(bar.observed_at, index)
        available_at_to_index.setdefault(bar.available_at, index)
    return _LegacyBarTimestampIndex(
        observed_at_to_index=observed_at_to_index,
        available_at_to_index=available_at_to_index,
    )


@dataclass(frozen=True, slots=True)
class _LegacyBarTimestampIndex:
    observed_at_to_index: dict[datetime, int]
    available_at_to_index: dict[datetime, int]


def _resolve_signal_bar_index(
    bar_index: _LegacyBarTimestampIndex,
    *,
    available_at: datetime,
) -> int | None:
    observed_match = bar_index.observed_at_to_index.get(available_at)
    if observed_match is not None:
        return observed_match
    return bar_index.available_at_to_index.get(available_at)


def _closed_pnl_by_exit_observed_at(
    trades: Sequence[SimulatedTrade],
) -> dict[datetime, Decimal]:
    closed_pnl: dict[datetime, Decimal] = {}
    for trade in trades:
        closed_pnl[trade.exit_fill_at] = (
            closed_pnl.get(trade.exit_fill_at, Decimal("0")) + trade.net_pnl
        )
    return closed_pnl


__all__ = [
    "_build_bar_timestamp_index",
    "_closed_pnl_by_exit_observed_at",
    "_observed_at_index_by_ns",
    "_open_position_counts_by_bar_index",
    "_resolve_signal_bar_index",
]
