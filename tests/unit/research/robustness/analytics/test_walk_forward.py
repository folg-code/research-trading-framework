"""Unit tests for walk-forward analytics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.analytics.parameter_sweep import (
    SweepMetric,
    SweepRunMetrics,
)
from trading_framework.research.robustness.analytics.walk_forward import (
    select_best_train_config,
    stitch_oos_equity_curves,
)
from trading_framework.research.robustness.walk_forward import WalkForwardFold


def _summary(net_pnl: str) -> StrategyRunSummary:
    return StrategyRunSummary(
        trade_count=5,
        win_count=3,
        loss_count=2,
        win_rate=0.6,
        gross_pnl=Decimal(net_pnl),
        net_pnl=Decimal(net_pnl),
        total_commission=Decimal("0"),
        max_drawdown=Decimal("-10"),
        final_equity=Decimal("10000") + Decimal(net_pnl),
    )


def _train_run(config_id: str, net_pnl: str) -> SweepRunMetrics:
    return SweepRunMetrics(
        config_id=config_id,
        config_fingerprint=config_id,
        parameter_overrides={"exit_after_bars": config_id},
        strategy_run_id=f"run-{config_id}",
        summary=_summary(net_pnl),
    )


def test_select_best_train_config_uses_train_metrics_only() -> None:
    fold = WalkForwardFold(
        fold_id="fold_000",
        fold_index=0,
        train_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        oos_range=TimeRange(
            start=datetime(2024, 1, 2, tzinfo=UTC),
            end=datetime(2024, 1, 3, tzinfo=UTC),
        ),
    )
    selection = select_best_train_config(
        fold=fold,
        train_runs=(
            _train_run("a", "100"),
            _train_run("b", "250"),
        ),
        selection_metric=SweepMetric.NET_PNL,
    )
    assert selection.config_id == "b"
    assert selection.train_net_pnl == Decimal("250")


def test_stitch_oos_equity_curves_concatenates_with_continuous_levels() -> None:
    first = pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
            ],
            "equity": [10000.0, 10050.0],
            "drawdown": [0.0, -5.0],
            "open_position_count": [0, 0],
        }
    )
    second = pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 2, 10, 0, tzinfo=UTC),
                datetime(2024, 1, 2, 11, 0, tzinfo=UTC),
            ],
            "equity": [10000.0, 10020.0],
            "drawdown": [0.0, -3.0],
            "open_position_count": [0, 0],
        }
    )

    stitched = stitch_oos_equity_curves(fold_segments=((0, first), (1, second)))

    assert stitched.fold_count == 2
    assert stitched.point_count == 4
    assert float(stitched.equity.row(2, named=True)["equity"]) == pytest.approx(10050.0)
    assert float(stitched.equity.row(3, named=True)["equity"]) == pytest.approx(10070.0)
