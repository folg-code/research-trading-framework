"""Bar-sequential Strategy Research simulation engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation.assumptions import (
    SimulationAssumptions,
    apply_entry_slippage,
    apply_exit_slippage,
)
from trading_framework.research.simulation.compile import (
    compile_simulation_input,
    datetime_to_epoch_ns,
    epoch_ns_to_datetime,
)
from trading_framework.research.simulation.facts import (
    EquityPoint,
    SimulatedTrade,
    derive_trade_id,
    equity_points_to_dataframe,
    simulated_trades_to_dataframe,
)
from trading_framework.research.simulation.input import (
    SIGNAL_DIRECTION_LONG,
    UNRESOLVED_BAR_INDEX,
    CompiledSimulationInput,
)
from trading_framework.signal_model.definitions import SignalDirection
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
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
        exit_model = _require_fixed_bars_exit(strategy_model)
        risk_model = _require_fixed_quantity_risk(strategy_model)
        compiled = compile_simulation_input(
            bars=ordered_bars,
            entry_signals=entry_signals,
        )

        trades = self._simulate_trades(
            compiled=compiled,
            strategy_model=strategy_model,
            assumptions=assumptions,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
            exit_model=exit_model,
            risk_model=risk_model,
        )
        equity = self._build_equity_curve(
            compiled=compiled,
            trades=trades,
            assumptions=assumptions,
        )
        return SimulationResult(
            trades=simulated_trades_to_dataframe(trades),
            equity=equity_points_to_dataframe(equity),
        )

    def _simulate_trades(
        self,
        *,
        compiled: CompiledSimulationInput,
        strategy_model: StrategyModelDefinition,
        assumptions: SimulationAssumptions,
        instrument: str,
        source_dataset_ref: str,
        exit_model: FixedBarsExitModel,
        risk_model: FixedQuantityRiskModel,
    ) -> list[SimulatedTrade]:
        bar_series = compiled.bars
        signal_series = compiled.entry_signals
        bar_count = bar_series.bar_count
        trades: list[SimulatedTrade] = []
        position_open_until_bar_index: int | None = None
        quantity = risk_model.position_quantity()

        for signal_index in range(signal_series.available_at_ns.shape[0]):
            signal_bar_index = int(signal_series.signal_bar_index[signal_index])
            if signal_bar_index == UNRESOLVED_BAR_INDEX:
                continue

            entry_fill_bar_index = signal_bar_index + 1
            if entry_fill_bar_index >= bar_count:
                continue
            if (
                position_open_until_bar_index is not None
                and entry_fill_bar_index <= position_open_until_bar_index
            ):
                continue

            exit_signal_bar_index = exit_model.exit_bar_index(
                entry_fill_bar_index=entry_fill_bar_index
            )
            exit_fill_bar_index = exit_signal_bar_index + 1
            if exit_fill_bar_index >= bar_count:
                continue

            direction = _decode_signal_direction(int(signal_series.direction[signal_index]))
            entry_signal_at = epoch_ns_to_datetime(int(signal_series.available_at_ns[signal_index]))
            entry_fill_at = epoch_ns_to_datetime(
                int(bar_series.observed_at_ns[entry_fill_bar_index])
            )
            exit_signal_at = epoch_ns_to_datetime(
                int(bar_series.observed_at_ns[exit_signal_bar_index])
            )
            exit_fill_at = epoch_ns_to_datetime(int(bar_series.observed_at_ns[exit_fill_bar_index]))

            entry_fill_price = apply_entry_slippage(
                price=_price_from_array(bar_series.open_prices[entry_fill_bar_index]),
                direction=direction,
                slippage_bps=assumptions.slippage_bps,
            )
            exit_fill_price = apply_exit_slippage(
                price=_price_from_array(bar_series.open_prices[exit_fill_bar_index]),
                direction=direction,
                slippage_bps=assumptions.slippage_bps,
            )
            gross_pnl = _gross_pnl(
                direction=direction,
                quantity=quantity,
                entry_fill_price=entry_fill_price,
                exit_fill_price=exit_fill_price,
            )
            commission_paid = assumptions.commission_per_side * Decimal("2")
            net_pnl = gross_pnl - commission_paid

            trades.append(
                SimulatedTrade(
                    trade_id=derive_trade_id(
                        strategy_model_id=strategy_model.strategy_model_id,
                        entry_signal_at=entry_signal_at,
                        direction=direction.value,
                    ),
                    strategy_model_id=strategy_model.strategy_model_id,
                    instrument=instrument,
                    direction=direction.value,
                    entry_signal_at=entry_signal_at,
                    entry_fill_at=entry_fill_at,
                    entry_fill_price=entry_fill_price,
                    exit_signal_at=exit_signal_at,
                    exit_fill_at=exit_fill_at,
                    exit_fill_price=exit_fill_price,
                    quantity=quantity,
                    gross_pnl=gross_pnl,
                    commission_paid=commission_paid,
                    net_pnl=net_pnl,
                    bars_held=exit_fill_bar_index - entry_fill_bar_index,
                    exit_reason=exit_model.default_exit_reason,
                    source_dataset_ref=source_dataset_ref,
                )
            )
            position_open_until_bar_index = exit_fill_bar_index

        return trades

    def _build_equity_curve(
        self,
        *,
        compiled: CompiledSimulationInput,
        trades: list[SimulatedTrade],
        assumptions: SimulationAssumptions,
    ) -> list[EquityPoint]:
        bar_series = compiled.bars
        closed_pnl_by_exit_ns = _closed_pnl_by_exit_observed_at_ns(trades)
        open_counts = _open_position_counts_by_bar_index(
            trades,
            observed_at_to_index=_observed_at_index_by_ns(bar_series.observed_at_ns),
            bar_count=bar_series.bar_count,
        )
        equity = assumptions.initial_capital
        peak_equity = equity
        points: list[EquityPoint] = []

        for index in range(bar_series.bar_count):
            observed_at_ns = int(bar_series.observed_at_ns[index])
            equity += closed_pnl_by_exit_ns.get(observed_at_ns, Decimal("0"))
            peak_equity = max(peak_equity, equity)
            drawdown = equity - peak_equity
            points.append(
                EquityPoint(
                    observed_at=epoch_ns_to_datetime(observed_at_ns),
                    equity=equity,
                    drawdown=drawdown,
                    open_position_count=open_counts[index],
                )
            )
        return points


def _observed_at_index_by_ns(observed_at_ns: np.ndarray) -> dict[int, int]:
    index_by_timestamp: dict[int, int] = {}
    for index, timestamp_ns in enumerate(observed_at_ns.tolist()):
        index_by_timestamp.setdefault(int(timestamp_ns), index)
    return index_by_timestamp


def _closed_pnl_by_exit_observed_at_ns(
    trades: Sequence[SimulatedTrade],
) -> dict[int, Decimal]:
    closed_pnl: dict[int, Decimal] = {}
    for trade in trades:
        exit_at_ns = datetime_to_epoch_ns(trade.exit_fill_at)
        closed_pnl[exit_at_ns] = closed_pnl.get(exit_at_ns, Decimal("0")) + trade.net_pnl
    return closed_pnl


def _open_position_counts_by_bar_index(
    trades: Sequence[SimulatedTrade],
    *,
    observed_at_to_index: dict[int, int],
    bar_count: int,
) -> list[int]:
    if bar_count == 0:
        return []

    open_delta = [0] * bar_count
    for trade in trades:
        entry_index = observed_at_to_index.get(datetime_to_epoch_ns(trade.entry_fill_at))
        exit_index = observed_at_to_index.get(datetime_to_epoch_ns(trade.exit_fill_at))
        if entry_index is None or exit_index is None:
            continue
        open_delta[entry_index] += 1
        open_delta[exit_index] -= 1

    open_counts: list[int] = []
    running_open = 0
    for delta in open_delta:
        running_open += delta
        open_counts.append(running_open)
    return open_counts


def _validate_entry_signals(entry_signals: pl.DataFrame) -> None:
    required = {"available_at", "direction"}
    missing = required.difference(entry_signals.columns)
    if missing:
        msg = f"entry_signals missing required columns: {sorted(missing)}"
        raise SimulationEngineError(msg)


def _require_fixed_bars_exit(strategy_model: StrategyModelDefinition) -> FixedBarsExitModel:
    exit_model = strategy_model.exit_model
    if not isinstance(exit_model, FixedBarsExitModel):
        msg = "BarSequentialSimulator supports FixedBarsExitModel only"
        raise SimulationEngineError(msg)
    return exit_model


def _require_fixed_quantity_risk(strategy_model: StrategyModelDefinition) -> FixedQuantityRiskModel:
    risk_model = strategy_model.risk_model
    if not isinstance(risk_model, FixedQuantityRiskModel):
        msg = "BarSequentialSimulator supports FixedQuantityRiskModel only"
        raise SimulationEngineError(msg)
    return risk_model


def _decode_signal_direction(direction_code: int) -> SignalDirection:
    if direction_code == SIGNAL_DIRECTION_LONG:
        return SignalDirection.LONG
    return SignalDirection.SHORT


def _price_from_array(value: float) -> Decimal:
    return Decimal(str(value))


def _gross_pnl(
    *,
    direction: SignalDirection,
    quantity: Decimal,
    entry_fill_price: Decimal,
    exit_fill_price: Decimal,
) -> Decimal:
    price_delta = exit_fill_price - entry_fill_price
    if direction is SignalDirection.LONG:
        return price_delta * quantity
    return -price_delta * quantity


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
