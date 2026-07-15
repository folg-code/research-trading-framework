"""Stress testing analytics — post-processors and comparison tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.strategy_summarize import (
    StrategyRunSummary,
    summarize_strategy_run,
)
from trading_framework.research.robustness.stress import StressScenarioResult, StressScenarioSpec


class StressAnalyticsError(ValidationError):
    """Raised when stress analytics inputs are invalid."""


@dataclass(frozen=True, slots=True)
class StressComparisonRow:
    """One row in a baseline-vs-scenario comparison table."""

    scenario_id: str
    mode: str
    status: str
    net_pnl: Decimal | None
    trade_count: int | None
    delta_net_pnl: Decimal | None
    strategy_run_id: str | None


@dataclass(frozen=True, slots=True)
class StressTestAnalytics:
    """Bundled stress comparison analytics for one experiment."""

    experiment_id: str
    baseline_strategy_run_id: str
    baseline_net_pnl: Decimal
    baseline_trade_count: int
    rows: tuple[StressComparisonRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "baseline_strategy_run_id": self.baseline_strategy_run_id,
            "baseline_net_pnl": str(self.baseline_net_pnl),
            "baseline_trade_count": self.baseline_trade_count,
            "rows": [_row_to_dict(row) for row in self.rows],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StressTestAnalytics:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            baseline_strategy_run_id=str(payload["baseline_strategy_run_id"]),
            baseline_net_pnl=Decimal(str(payload["baseline_net_pnl"])),
            baseline_trade_count=int(payload["baseline_trade_count"]),
            rows=tuple(_row_from_dict(row) for row in payload["rows"]),
        )


def apply_remove_top_trades_stress(
    *,
    trades: pl.DataFrame,
    equity: pl.DataFrame,
    scenario: StressScenarioSpec,
    initial_capital: Decimal,
) -> tuple[pl.DataFrame, pl.DataFrame, StrategyRunSummary]:
    """Remove top-N trades by net PnL and rebuild equity."""
    if scenario.remove_top_n_trades <= 0:
        msg = "remove_top_n_trades must be positive"
        raise StressAnalyticsError(msg)
    if len(trades) == 0:
        summary = summarize_strategy_run(trades=trades, equity=equity)
        return trades, equity, summary

    remove_count = min(scenario.remove_top_n_trades, len(trades))
    top_trade_ids = (
        trades.sort("net_pnl", descending=True).head(remove_count).get_column("trade_id").to_list()
    )
    filtered_trades = trades.filter(~pl.col("trade_id").is_in(top_trade_ids))
    filtered_equity = rebuild_equity_from_trades(
        trades=filtered_trades,
        template_equity=equity,
        initial_capital=initial_capital,
    )
    summary = summarize_strategy_run(trades=filtered_trades, equity=filtered_equity)
    return filtered_trades, filtered_equity, summary


def apply_remove_top_days_stress(
    *,
    trades: pl.DataFrame,
    equity: pl.DataFrame,
    scenario: StressScenarioSpec,
    initial_capital: Decimal,
) -> tuple[pl.DataFrame, pl.DataFrame, StrategyRunSummary]:
    """Remove top-N session days by aggregated net PnL and rebuild equity."""
    if scenario.remove_top_n_days <= 0:
        msg = "remove_top_n_days must be positive"
        raise StressAnalyticsError(msg)
    if len(trades) == 0:
        summary = summarize_strategy_run(trades=trades, equity=equity)
        return trades, equity, summary

    trades_with_day = trades.with_columns(
        session_day=pl.col("exit_fill_at").dt.date().cast(pl.Utf8)
    )
    day_pnl = trades_with_day.group_by("session_day").agg(pl.col("net_pnl").sum().alias("day_pnl"))
    remove_count = min(scenario.remove_top_n_days, len(day_pnl))
    top_days = (
        day_pnl.sort("day_pnl", descending=True)
        .head(remove_count)
        .get_column("session_day")
        .to_list()
    )
    filtered_trades = trades_with_day.filter(~pl.col("session_day").is_in(top_days)).drop(
        "session_day"
    )
    filtered_equity = rebuild_equity_from_trades(
        trades=filtered_trades,
        template_equity=equity,
        initial_capital=initial_capital,
    )
    summary = summarize_strategy_run(trades=filtered_trades, equity=filtered_equity)
    return filtered_trades, filtered_equity, summary


def rebuild_equity_from_trades(
    *,
    trades: pl.DataFrame,
    template_equity: pl.DataFrame,
    initial_capital: Decimal,
) -> pl.DataFrame:
    """Rebuild equity on the template timeline from filtered trades."""
    if len(template_equity) == 0:
        return template_equity

    ordered_trades = trades.sort("exit_fill_at")
    exit_times: list[datetime] = []
    cumulative_pnls: list[Decimal] = []
    running = Decimal("0")
    for row in ordered_trades.iter_rows(named=True):
        exit_fill_at = row["exit_fill_at"]
        if not isinstance(exit_fill_at, datetime):
            msg = "trades.exit_fill_at must be datetime"
            raise StressAnalyticsError(msg)
        running += Decimal(str(row["net_pnl"]))
        exit_times.append(exit_fill_at)
        cumulative_pnls.append(running)

    equity_values: list[float] = []
    trade_index = 0
    active_pnl = Decimal("0")
    for observed_at in template_equity.sort("observed_at").get_column("observed_at"):
        if not isinstance(observed_at, datetime):
            msg = "equity.observed_at must be datetime"
            raise StressAnalyticsError(msg)
        while trade_index < len(exit_times) and exit_times[trade_index] <= observed_at:
            active_pnl = cumulative_pnls[trade_index]
            trade_index += 1
        equity_values.append(float(initial_capital + active_pnl))

    rebuilt = template_equity.sort("observed_at").with_columns(
        equity=pl.Series("equity", equity_values),
    )
    return rebuilt.with_columns(drawdown=pl.col("equity") - pl.col("equity").cum_max())


def build_stress_comparison_table(
    *,
    experiment_id: str,
    baseline_summary: StrategyRunSummary,
    baseline_strategy_run_id: str,
    scenario_results: tuple[StressScenarioResult, ...],
) -> StressTestAnalytics:
    """Build baseline-vs-scenario comparison rows."""
    rows: list[StressComparisonRow] = []
    for result in scenario_results:
        net_pnl = Decimal(result.net_pnl) if result.net_pnl is not None else None
        delta = None
        if net_pnl is not None:
            delta = net_pnl - baseline_summary.net_pnl
        rows.append(
            StressComparisonRow(
                scenario_id=result.scenario_id,
                mode=result.mode,
                status=result.status,
                net_pnl=net_pnl,
                trade_count=result.trade_count,
                delta_net_pnl=delta,
                strategy_run_id=result.strategy_run_id,
            )
        )
    return StressTestAnalytics(
        experiment_id=experiment_id,
        baseline_strategy_run_id=baseline_strategy_run_id,
        baseline_net_pnl=baseline_summary.net_pnl,
        baseline_trade_count=baseline_summary.trade_count,
        rows=tuple(rows),
    )


def _row_to_dict(row: StressComparisonRow) -> dict[str, Any]:
    return {
        "scenario_id": row.scenario_id,
        "mode": row.mode,
        "status": row.status,
        "net_pnl": str(row.net_pnl) if row.net_pnl is not None else None,
        "trade_count": row.trade_count,
        "delta_net_pnl": str(row.delta_net_pnl) if row.delta_net_pnl is not None else None,
        "strategy_run_id": row.strategy_run_id,
    }


def _row_from_dict(payload: dict[str, Any]) -> StressComparisonRow:
    net_pnl = payload.get("net_pnl")
    delta = payload.get("delta_net_pnl")
    return StressComparisonRow(
        scenario_id=str(payload["scenario_id"]),
        mode=str(payload["mode"]),
        status=str(payload["status"]),
        net_pnl=Decimal(str(net_pnl)) if net_pnl is not None else None,
        trade_count=(
            int(payload["trade_count"]) if payload.get("trade_count") is not None else None
        ),
        delta_net_pnl=Decimal(str(delta)) if delta is not None else None,
        strategy_run_id=(
            str(payload["strategy_run_id"]) if payload.get("strategy_run_id") is not None else None
        ),
    )
