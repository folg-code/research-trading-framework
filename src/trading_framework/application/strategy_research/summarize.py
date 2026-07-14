"""Summarize persisted Strategy Research trade and equity facts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import polars as pl


@dataclass(frozen=True, slots=True)
class StrategyRunSummary:
    """Minimal read-only summary metrics for one Strategy Research run."""

    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float | None
    gross_pnl: Decimal
    net_pnl: Decimal
    total_commission: Decimal
    max_drawdown: Decimal
    final_equity: Decimal


def summarize_strategy_run(*, trades: pl.DataFrame, equity: pl.DataFrame) -> StrategyRunSummary:
    """Compute MVP summary metrics from persisted fact tables."""
    trade_count = len(trades)
    if trade_count == 0:
        final_equity = _final_equity(equity)
        return StrategyRunSummary(
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=None,
            gross_pnl=Decimal("0"),
            net_pnl=Decimal("0"),
            total_commission=Decimal("0"),
            max_drawdown=_max_drawdown(equity),
            final_equity=final_equity,
        )

    net_pnls = trades.get_column("net_pnl")
    win_count = int((net_pnls > 0).sum())
    loss_count = int((net_pnls < 0).sum())
    win_rate = win_count / trade_count

    return StrategyRunSummary(
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        gross_pnl=_sum_decimal(trades, "gross_pnl"),
        net_pnl=_sum_decimal(trades, "net_pnl"),
        total_commission=_sum_decimal(trades, "commission_paid"),
        max_drawdown=_max_drawdown(equity),
        final_equity=_final_equity(equity),
    )


def _sum_decimal(frame: pl.DataFrame, column: str) -> Decimal:
    if len(frame) == 0:
        return Decimal("0")
    return Decimal(str(frame[column].sum()))


def _max_drawdown(equity: pl.DataFrame) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    return Decimal(str(equity["drawdown"].min()))


def _final_equity(equity: pl.DataFrame) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    ordered = equity.sort("observed_at")
    return Decimal(str(ordered.row(-1, named=True)["equity"]))
