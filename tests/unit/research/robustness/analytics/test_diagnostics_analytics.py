"""Unit tests for statistical diagnostics analytics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl

from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.analytics.diagnostics import (
    compute_is_oos_degradation,
    compute_pnl_concentration,
    compute_temporal_stability,
)
from trading_framework.research.robustness.analytics.parameter_sweep import SweepMetric
from trading_framework.research.robustness.analytics.walk_forward import (
    WalkForwardFoldEvaluation,
    WalkForwardTrainSelection,
)
from trading_framework.research.robustness.diagnostics import TimeBucketMode
from trading_framework.research.robustness.walk_forward import WalkForwardFold
from trading_framework.research.simulation.facts import simulated_trade_schema


def _sample_trades() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "trade_id": ["t1", "t2", "t3"],
            "strategy_model_id": ["s", "s", "s"],
            "instrument": ["ES.c.0", "ES.c.0", "ES.c.0"],
            "direction": ["long", "long", "short"],
            "entry_signal_at": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 2, 1, tzinfo=UTC),
                datetime(2024, 2, 15, tzinfo=UTC),
            ],
            "entry_fill_at": [
                datetime(2024, 1, 1, 14, 1, tzinfo=UTC),
                datetime(2024, 2, 1, 14, 1, tzinfo=UTC),
                datetime(2024, 2, 15, 14, 1, tzinfo=UTC),
            ],
            "entry_fill_price": [100.0, 100.0, 100.0],
            "exit_signal_at": [
                datetime(2024, 1, 1, 14, 5, tzinfo=UTC),
                datetime(2024, 2, 1, 14, 5, tzinfo=UTC),
                datetime(2024, 2, 15, 14, 5, tzinfo=UTC),
            ],
            "exit_fill_at": [
                datetime(2024, 1, 1, 14, 6, tzinfo=UTC),
                datetime(2024, 2, 1, 14, 6, tzinfo=UTC),
                datetime(2024, 2, 15, 14, 6, tzinfo=UTC),
            ],
            "exit_fill_price": [101.0, 99.0, 102.0],
            "quantity": [1.0, 1.0, 1.0],
            "gross_pnl": [10.0, -5.0, 20.0],
            "commission_paid": [1.0, 1.0, 1.0],
            "net_pnl": [9.0, -6.0, 19.0],
            "bars_held": [3, 5, 7],
            "exit_reason": ["fixed_bars", "fixed_bars", "fixed_bars"],
            "source_dataset_ref": ["dataset@1", "dataset@1", "dataset@1"],
        },
        schema=simulated_trade_schema(),
    )


def _summary(net_pnl: str) -> StrategyRunSummary:
    value = Decimal(net_pnl)
    return StrategyRunSummary(
        trade_count=1,
        win_count=1 if value > 0 else 0,
        loss_count=1 if value < 0 else 0,
        win_rate=1.0 if value > 0 else 0.0,
        gross_pnl=value,
        net_pnl=value,
        total_commission=Decimal("0"),
        max_drawdown=Decimal("-1"),
        final_equity=Decimal("100000") + value,
    )


def test_compute_temporal_stability_buckets_by_month() -> None:
    metrics = compute_temporal_stability(
        trades=_sample_trades(),
        bucket_mode=TimeBucketMode.MONTH,
    )
    assert metrics.bucket_count == 2
    assert metrics.net_pnl_range == Decimal("4")


def test_compute_pnl_concentration_reports_top_trade_share() -> None:
    metrics = compute_pnl_concentration(
        trades=_sample_trades(),
        top_k_trades=1,
        top_k_days=1,
    )
    assert metrics.top_trade_ids == ("t3",)
    assert metrics.top_trades_share == Decimal("19") / Decimal("22")


def test_compute_is_oos_degradation_links_walk_forward_folds() -> None:
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
    evaluation = WalkForwardFoldEvaluation(
        fold=fold,
        selection=WalkForwardTrainSelection(
            fold_id=fold.fold_id,
            fold_index=0,
            config_id="a",
            parameter_overrides={"exit_after_bars": "5"},
            strategy_run_id="run-train",
            selection_metric=SweepMetric.NET_PNL,
            train_metric_value=Decimal("100"),
            train_net_pnl=Decimal("100"),
        ),
        oos_strategy_run_id="run-oos",
        oos_summary=_summary("40"),
    )
    metrics = compute_is_oos_degradation(fold_evaluations=(evaluation,))
    assert metrics.fold_rows[0].degradation_delta == Decimal("-60")
    assert metrics.oos_beats_train_count == 0
