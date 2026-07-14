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

        trades = self._simulate_trades(
            bars=ordered_bars,
            entry_signals=entry_signals,
            strategy_model=strategy_model,
            assumptions=assumptions,
            instrument=instrument,
            source_dataset_ref=source_dataset_ref,
            exit_model=exit_model,
            risk_model=risk_model,
        )
        equity = self._build_equity_curve(
            bars=ordered_bars,
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
        bars: Sequence[MarketBar],
        entry_signals: pl.DataFrame,
        strategy_model: StrategyModelDefinition,
        assumptions: SimulationAssumptions,
        instrument: str,
        source_dataset_ref: str,
        exit_model: FixedBarsExitModel,
        risk_model: FixedQuantityRiskModel,
    ) -> list[SimulatedTrade]:
        trades: list[SimulatedTrade] = []
        position_open_until_bar_index: int | None = None
        sorted_signals = entry_signals.sort("available_at")

        for row in sorted_signals.iter_rows(named=True):
            available_at = row["available_at"]
            direction = SignalDirection(str(row["direction"]))
            signal_bar_index = _resolve_signal_bar_index(bars, available_at=available_at)
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
    ) -> list[EquityPoint]:
        equity = assumptions.initial_capital
        peak_equity = equity
        points: list[EquityPoint] = []

        for bar in bars:
            closed_pnl = sum(
                (trade.net_pnl for trade in trades if trade.exit_fill_at == bar.observed_at),
                start=Decimal("0"),
            )
            equity += closed_pnl
            peak_equity = max(peak_equity, equity)
            drawdown = equity - peak_equity
            open_position_count = sum(
                1 for trade in trades if trade.entry_fill_at <= bar.observed_at < trade.exit_fill_at
            )
            points.append(
                EquityPoint(
                    observed_at=bar.observed_at,
                    equity=equity,
                    drawdown=drawdown,
                    open_position_count=open_position_count,
                )
            )
        return points


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


def _resolve_signal_bar_index(bars: Sequence[MarketBar], *, available_at: datetime) -> int | None:
    for index, bar in enumerate(bars):
        if bar.observed_at == available_at:
            return index
    for index, bar in enumerate(bars):
        if bar.available_at == available_at:
            return index
    return None


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
