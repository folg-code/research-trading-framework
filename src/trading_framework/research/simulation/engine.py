"""Bar-sequential Strategy Research simulation engine."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.research.simulation.assumptions import (
    SimulationAssumptions,
    apply_entry_slippage,
    apply_exit_slippage,
)
from trading_framework.research.simulation.facts import (
    EquityPoint,
    SimulatedTrade,
    derive_trade_id,
    equity_points_to_dataframe,
    simulated_trades_to_dataframe,
)
from trading_framework.signal_model.definitions import SignalDirection
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition


class SimulationEngineError(ValidationError):
    """Raised when bar-sequential simulation inputs are invalid."""


@dataclass(frozen=True, slots=True)
class _BarTimestampIndex:
    """Lookup bar index by observed_at or available_at without scanning all bars."""

    observed_at_to_index: dict[datetime, int]
    available_at_to_index: dict[datetime, int]


def _build_bar_timestamp_index(bars: Sequence[MarketBar]) -> _BarTimestampIndex:
    observed_at_to_index: dict[datetime, int] = {}
    available_at_to_index: dict[datetime, int] = {}
    for index, bar in enumerate(bars):
        observed_at_to_index.setdefault(bar.observed_at, index)
        available_at_to_index.setdefault(bar.available_at, index)
    return _BarTimestampIndex(
        observed_at_to_index=observed_at_to_index,
        available_at_to_index=available_at_to_index,
    )


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

        bar_index = _build_bar_timestamp_index(ordered_bars)

        trades = self._simulate_trades(
            bars=ordered_bars,
            entry_signals=entry_signals,
            strategy_model=strategy_model,
            assumptions=assumptions,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
            exit_model=exit_model,
            risk_model=risk_model,
            bar_index=bar_index,
        )
        equity = self._build_equity_curve(
            bars=ordered_bars,
            trades=trades,
            assumptions=assumptions,
            bar_index=bar_index,
        )
        return SimulationResult(
            trades=simulated_trades_to_dataframe(trades),
            equity=equity_points_to_dataframe(equity),
        )

    def _simulate_trades(
        self,
        *,
        bars: Sequence[MarketBar],
        entry_signals: pl.DataFrame,
        strategy_model: StrategyModelDefinition,
        assumptions: SimulationAssumptions,
        instrument: str,
        source_dataset_ref: str,
        exit_model: FixedBarsExitModel,
        risk_model: FixedQuantityRiskModel,
        bar_index: _BarTimestampIndex,
    ) -> list[SimulatedTrade]:
        trades: list[SimulatedTrade] = []
        position_open_until_bar_index: int | None = None
        sorted_signals = entry_signals.sort("available_at")

        for row in sorted_signals.iter_rows(named=True):
            available_at = row["available_at"]
            direction = SignalDirection(str(row["direction"]))
            signal_bar_index = _resolve_signal_bar_index(bar_index, available_at=available_at)
            if signal_bar_index is None:
                continue

            entry_fill_bar_index = signal_bar_index + 1
            if entry_fill_bar_index >= len(bars):
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
            if exit_fill_bar_index >= len(bars):
                continue

            entry_bar = bars[entry_fill_bar_index]
            exit_bar = bars[exit_fill_bar_index]
            exit_signal_bar = bars[exit_signal_bar_index]
            quantity = risk_model.position_quantity()

            entry_fill_price = apply_entry_slippage(
                price=entry_bar.open.value,
                direction=direction,
                slippage_bps=assumptions.slippage_bps,
            )
            exit_fill_price = apply_exit_slippage(
                price=exit_bar.open.value,
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
                        entry_signal_at=available_at,
                        direction=direction.value,
                    ),
                    strategy_model_id=strategy_model.strategy_model_id,
                    instrument=instrument,
                    direction=direction.value,
                    entry_signal_at=available_at,
                    entry_fill_at=entry_bar.observed_at,
                    entry_fill_price=entry_fill_price,
                    exit_signal_at=exit_signal_bar.observed_at,
                    exit_fill_at=exit_bar.observed_at,
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
        bars: Sequence[MarketBar],
        trades: list[SimulatedTrade],
        assumptions: SimulationAssumptions,
        bar_index: _BarTimestampIndex,
    ) -> list[EquityPoint]:
        closed_pnl_by_exit = _closed_pnl_by_exit_observed_at(trades)
        open_counts = _open_position_counts_by_bar_index(
            trades,
            bar_index=bar_index,
            bar_count=len(bars),
        )
        equity = assumptions.initial_capital
        peak_equity = equity
        points: list[EquityPoint] = []

        for index, bar in enumerate(bars):
            equity += closed_pnl_by_exit.get(bar.observed_at, Decimal("0"))
            peak_equity = max(peak_equity, equity)
            drawdown = equity - peak_equity
            points.append(
                EquityPoint(
                    observed_at=bar.observed_at,
                    equity=equity,
                    drawdown=drawdown,
                    open_position_count=open_counts[index],
                )
            )
        return points


def _closed_pnl_by_exit_observed_at(
    trades: Sequence[SimulatedTrade],
) -> dict[datetime, Decimal]:
    closed_pnl: dict[datetime, Decimal] = {}
    for trade in trades:
        closed_pnl[trade.exit_fill_at] = (
            closed_pnl.get(trade.exit_fill_at, Decimal("0")) + trade.net_pnl
        )
    return closed_pnl


def _open_position_counts_by_bar_index(
    trades: Sequence[SimulatedTrade],
    *,
    bar_index: _BarTimestampIndex,
    bar_count: int,
) -> list[int]:
    if bar_count == 0:
        return []

    open_delta = [0] * bar_count
    for trade in trades:
        entry_index = bar_index.observed_at_to_index.get(trade.entry_fill_at)
        exit_index = bar_index.observed_at_to_index.get(trade.exit_fill_at)
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


def _resolve_signal_bar_index(
    bar_index: _BarTimestampIndex,
    *,
    available_at: datetime,
) -> int | None:
    observed_match = bar_index.observed_at_to_index.get(available_at)
    if observed_match is not None:
        return observed_match
    return bar_index.available_at_to_index.get(available_at)


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
