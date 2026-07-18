"""Serialize Strategy Research overview KPIs to a dashboard Parquet row."""

from __future__ import annotations

from decimal import Decimal

import polars as pl

from trading_framework.research.analytics.strategy_dashboard import StrategyDashboardOverviewKpis

STRATEGY_RESEARCH_ANALYTICS_SCHEMA_VERSION = "strategy_research_analytics.v1"


def overview_kpis_to_summary_metrics_frame(
    *,
    run_id: str,
    overview: StrategyDashboardOverviewKpis,
) -> pl.DataFrame:
    """Return a one-row ``summary_metrics`` frame for dashboard KPI cards."""
    return pl.DataFrame(
        {
            "schema_version": [STRATEGY_RESEARCH_ANALYTICS_SCHEMA_VERSION],
            "run_id": [run_id],
            "net_pnl": [_decimal_str(overview.net_pnl)],
            "total_return": [overview.total_return],
            "max_drawdown": [_decimal_str(overview.max_drawdown)],
            "current_drawdown": [_decimal_str(overview.current_drawdown)],
            "sharpe_ratio": [overview.sharpe_ratio],
            "sortino_ratio": [overview.sortino_ratio],
            "profit_factor": [overview.profit_factor],
            "expectancy": [_optional_decimal_str(overview.expectancy)],
            "trade_count": [overview.trade_count],
            "win_rate": [overview.win_rate],
            "avg_win": [_optional_decimal_str(overview.avg_win)],
            "avg_loss": [_optional_decimal_str(overview.avg_loss)],
            "total_costs": [_decimal_str(overview.total_costs)],
        }
    )


def _decimal_str(value: Decimal) -> str:
    return str(value)


def _optional_decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)
