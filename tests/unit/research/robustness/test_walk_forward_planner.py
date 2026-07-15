"""Unit tests for walk-forward fold planning."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.robustness.walk_forward import (
    WalkForwardSpec,
    WalkForwardWindowMode,
    plan_walk_forward_folds,
)


def test_plan_walk_forward_folds_rolling_produces_non_overlapping_splits() -> None:
    overall = TimeRange(
        start=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    spec = WalkForwardSpec(
        window_mode=WalkForwardWindowMode.ROLLING,
        train_duration_seconds=4 * 3600,
        oos_duration_seconds=3600,
        step_duration_seconds=2 * 3600,
    )

    folds = plan_walk_forward_folds(
        overall_range=overall,
        spec=spec,
        bar_step=timedelta(minutes=1),
    )

    assert len(folds) >= 2
    for fold in folds:
        assert fold.train_range.end < fold.oos_range.start
        assert fold.oos_range.end <= overall.end


def test_plan_walk_forward_folds_expanding_grows_train_window() -> None:
    overall = TimeRange(
        start=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        end=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
    )
    spec = WalkForwardSpec(
        window_mode=WalkForwardWindowMode.EXPANDING,
        train_duration_seconds=2 * 3600,
        oos_duration_seconds=3600,
        step_duration_seconds=2 * 3600,
    )

    folds = plan_walk_forward_folds(
        overall_range=overall,
        spec=spec,
        bar_step=timedelta(minutes=1),
    )

    assert folds[0].train_range.start == overall.start
    assert folds[1].train_range.start == overall.start
    assert folds[1].train_range.end > folds[0].train_range.end


def test_plan_walk_forward_folds_rejects_range_without_folds() -> None:
    overall = TimeRange(
        start=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 1, 0, tzinfo=UTC),
    )
    spec = WalkForwardSpec(
        window_mode=WalkForwardWindowMode.ROLLING,
        train_duration_seconds=4 * 3600,
        oos_duration_seconds=3600,
        step_duration_seconds=3600,
    )
    with pytest.raises(ValidationError, match="no folds"):
        plan_walk_forward_folds(
            overall_range=overall,
            spec=spec,
            bar_step=timedelta(minutes=1),
        )
