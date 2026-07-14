"""Simulated trade and equity fact types for Strategy Research."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.strategy.exit_model import ExitReason


def simulated_trade_schema() -> dict[str, pl.DataType]:
    return {
        "trade_id": pl.String(),
        "strategy_model_id": pl.String(),
        "instrument": pl.String(),
        "direction": pl.String(),
        "entry_signal_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "entry_fill_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "entry_fill_price": pl.Float64(),
        "exit_signal_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "exit_fill_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "exit_fill_price": pl.Float64(),
        "quantity": pl.Float64(),
        "gross_pnl": pl.Float64(),
        "commission_paid": pl.Float64(),
        "net_pnl": pl.Float64(),
        "bars_held": pl.Int64(),
        "exit_reason": pl.String(),
        "source_dataset_ref": pl.String(),
    }


def equity_point_schema() -> dict[str, pl.DataType]:
    return {
        "observed_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "equity": pl.Float64(),
        "drawdown": pl.Float64(),
        "open_position_count": pl.Int64(),
    }


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    """One completed round-trip simulated trade."""

    trade_id: str
    strategy_model_id: str
    instrument: str
    direction: str
    entry_signal_at: datetime
    entry_fill_at: datetime
    entry_fill_price: Decimal
    exit_signal_at: datetime
    exit_fill_at: datetime
    exit_fill_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    commission_paid: Decimal
    net_pnl: Decimal
    bars_held: int
    exit_reason: ExitReason
    source_dataset_ref: str


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """Equity snapshot at one bar timestamp."""

    observed_at: datetime
    equity: Decimal
    drawdown: Decimal
    open_position_count: int


def derive_trade_id(
    *,
    strategy_model_id: str,
    entry_signal_at: datetime,
    direction: str,
) -> str:
    payload = f"{strategy_model_id}|{entry_signal_at.isoformat()}|{direction}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def empty_simulated_trades_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=simulated_trade_schema())


def empty_equity_points_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=equity_point_schema())


def simulated_trades_to_dataframe(trades: list[SimulatedTrade]) -> pl.DataFrame:
    if not trades:
        return empty_simulated_trades_dataframe()
    rows: list[dict[str, Any]] = []
    for trade in trades:
        rows.append(
            {
                "trade_id": trade.trade_id,
                "strategy_model_id": trade.strategy_model_id,
                "instrument": trade.instrument,
                "direction": trade.direction,
                "entry_signal_at": trade.entry_signal_at,
                "entry_fill_at": trade.entry_fill_at,
                "entry_fill_price": float(trade.entry_fill_price),
                "exit_signal_at": trade.exit_signal_at,
                "exit_fill_at": trade.exit_fill_at,
                "exit_fill_price": float(trade.exit_fill_price),
                "quantity": float(trade.quantity),
                "gross_pnl": float(trade.gross_pnl),
                "commission_paid": float(trade.commission_paid),
                "net_pnl": float(trade.net_pnl),
                "bars_held": trade.bars_held,
                "exit_reason": trade.exit_reason.value,
                "source_dataset_ref": trade.source_dataset_ref,
            }
        )
    return pl.DataFrame(rows, schema=simulated_trade_schema())


def equity_points_to_dataframe(points: list[EquityPoint]) -> pl.DataFrame:
    if not points:
        return empty_equity_points_dataframe()
    rows: list[dict[str, Any]] = []
    for point in points:
        rows.append(
            {
                "observed_at": point.observed_at,
                "equity": float(point.equity),
                "drawdown": float(point.drawdown),
                "open_position_count": point.open_position_count,
            }
        )
    return pl.DataFrame(rows, schema=equity_point_schema())
