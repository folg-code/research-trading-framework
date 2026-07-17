"""Tests for Strategy Research summary_metrics Parquet export."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import polars as pl

from tests.unit.research.datasets.test_strategy_research_repository import (
    _sample_envelope,
)
from trading_framework.infrastructure.storage.paths import strategy_research_summary_metrics_path
from trading_framework.research.analytics.strategy_dashboard import StrategyDashboardOverviewKpis
from trading_framework.research.analytics.strategy_summary_metrics_export import (
    STRATEGY_RESEARCH_ANALYTICS_SCHEMA_VERSION,
    overview_kpis_to_summary_metrics_frame,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
)


def test_overview_kpis_to_summary_metrics_frame() -> None:
    overview = StrategyDashboardOverviewKpis(
        net_pnl=Decimal("12.5"),
        total_return=0.01,
        max_drawdown=Decimal("-1.2"),
        current_drawdown=Decimal("-0.5"),
        sharpe_ratio=1.1,
        sortino_ratio=1.2,
        profit_factor=1.5,
        expectancy=Decimal("0.25"),
        trade_count=10,
        win_rate=0.6,
        avg_win=Decimal("1.0"),
        avg_loss=Decimal("-0.5"),
        total_costs=Decimal("0.1"),
    )
    frame = overview_kpis_to_summary_metrics_frame(run_id="st1", overview=overview)
    assert frame.height == 1
    row = frame.to_dicts()[0]
    assert row["schema_version"] == STRATEGY_RESEARCH_ANALYTICS_SCHEMA_VERSION
    assert row["run_id"] == "st1"
    assert row["net_pnl"] == "12.5"
    assert row["trade_count"] == 10


def test_strategy_repository_write_summary_metrics(tmp_path: Path) -> None:
    run_id = "st-metrics-1"
    repo = StrategyResearchDatasetRepository(tmp_path)
    repo.write(_sample_envelope(run_id=run_id))
    overview = StrategyDashboardOverviewKpis(
        net_pnl=Decimal("1"),
        total_return=None,
        max_drawdown=Decimal("0"),
        current_drawdown=Decimal("0"),
        sharpe_ratio=None,
        sortino_ratio=None,
        profit_factor=None,
        expectancy=None,
        trade_count=0,
        win_rate=None,
        avg_win=None,
        avg_loss=None,
        total_costs=Decimal("0"),
    )
    frame = overview_kpis_to_summary_metrics_frame(run_id=run_id, overview=overview)
    path = repo.write_summary_metrics(run_id, frame)
    assert path == strategy_research_summary_metrics_path(tmp_path, run_id)
    loaded = pl.read_parquet(path)
    assert loaded.height == 1
    assert loaded["run_id"][0] == run_id
