"""Tests for robustness analytics Parquet dual-write tables."""

from __future__ import annotations

from decimal import Decimal

from trading_framework.research.robustness.analytics.parameter_sweep import (
    ParameterSweepAnalytics,
    SweepMetric,
    SweepRankingRow,
)
from trading_framework.research.robustness.analytics.parquet_tables import (
    parameter_sweep_parquet_tables,
    stress_parquet_tables,
)
from trading_framework.research.robustness.analytics.stress import (
    StressComparisonRow,
    StressTestAnalytics,
)


def test_parameter_sweep_parquet_tables_rankings() -> None:
    analytics = ParameterSweepAnalytics(
        experiment_id="exp-1",
        ranking_metric=SweepMetric.NET_PNL,
        rankings=(
            SweepRankingRow(
                rank=1,
                config_id="c1",
                config_fingerprint="fp",
                parameter_overrides={"a": "1"},
                strategy_run_id="r1",
                metric=SweepMetric.NET_PNL,
                metric_value=Decimal("10"),
                net_pnl=Decimal("10"),
                max_drawdown=Decimal("-1"),
                win_rate=0.5,
                trade_count=4,
            ),
        ),
        neighbor_stability=(),
        heatmaps=(),
        isolated_optima=(),
    )
    tables = parameter_sweep_parquet_tables(analytics)
    assert tables["parameter_sweep_rankings"].height == 1
    assert tables["parameter_sweep_heatmap"].height == 0


def test_stress_parquet_tables() -> None:
    analytics = StressTestAnalytics(
        experiment_id="exp-1",
        baseline_strategy_run_id="base",
        baseline_net_pnl=Decimal("5"),
        baseline_trade_count=3,
        rows=(
            StressComparisonRow(
                scenario_id="s1",
                mode="cost",
                status="ok",
                net_pnl=Decimal("4"),
                trade_count=3,
                delta_net_pnl=Decimal("-1"),
                strategy_run_id="r2",
            ),
        ),
    )
    tables = stress_parquet_tables(analytics)
    assert tables["stress_comparison"].height == 1
