"""Tests for walk-forward fold geometry / stability (Phase 18 18D M1 / Sprint 075)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.robustness.analytics.fold_stability import (
    FOLD_GEOMETRY_SCHEMA_VERSION,
    STABILITY_SCHEMA_VERSION,
    compute_walk_forward_fold_geometry,
    compute_walk_forward_stability,
    empty_walk_forward_fold_geometry_dataframe,
    empty_walk_forward_stability_dataframe,
)
from trading_framework.research.robustness.walk_forward import WalkForwardFold, WalkForwardFoldPlan

_START = datetime(2025, 7, 14, 4, tzinfo=UTC)


def _fold(
    *, fold_index: int, train_start: datetime, train_days: int, oos_days: int
) -> WalkForwardFold:
    train_end = train_start + timedelta(days=train_days)
    oos_start = train_end + timedelta(minutes=1)
    oos_end = oos_start + timedelta(days=oos_days)
    return WalkForwardFold(
        fold_id=f"fold_{fold_index:03d}",
        fold_index=fold_index,
        train_range=TimeRange(start=train_start, end=train_end),
        oos_range=TimeRange(start=oos_start, end=oos_end),
    )


def test_compute_walk_forward_fold_geometry_empty_plan() -> None:
    plan = WalkForwardFoldPlan(experiment_id="e1", folds=())
    result = compute_walk_forward_fold_geometry(experiment_id="e1", plan=plan)
    assert result.height == 0
    assert result.columns == empty_walk_forward_fold_geometry_dataframe().columns


def test_compute_walk_forward_fold_geometry_first_fold_has_no_overlap() -> None:
    fold = _fold(fold_index=0, train_start=_START, train_days=45, oos_days=14)
    plan = WalkForwardFoldPlan(experiment_id="e1", folds=(fold,))
    result = compute_walk_forward_fold_geometry(experiment_id="e1", plan=plan)
    row = result.to_dicts()[0]
    assert row["schema_version"] == FOLD_GEOMETRY_SCHEMA_VERSION
    assert row["train_overlap_seconds_with_previous_fold"] == 0


def test_compute_walk_forward_fold_geometry_rolling_partial_overlap() -> None:
    """Mirrors the real demo experiment: train=45d, step=21d -> 24d overlap."""
    fold0 = _fold(fold_index=0, train_start=_START, train_days=45, oos_days=14)
    fold1 = _fold(fold_index=1, train_start=_START + timedelta(days=21), train_days=45, oos_days=14)
    plan = WalkForwardFoldPlan(experiment_id="e1", folds=(fold0, fold1))

    result = compute_walk_forward_fold_geometry(experiment_id="e1", plan=plan)

    rows = result.to_dicts()
    assert rows[1]["train_overlap_seconds_with_previous_fold"] == 24 * 86_400


def test_compute_walk_forward_fold_geometry_expanding_full_containment() -> None:
    """EXPANDING mode: train_start fixed, train_end grows -- full containment."""
    fold0 = _fold(fold_index=0, train_start=_START, train_days=45, oos_days=14)
    fold1 = _fold(fold_index=1, train_start=_START, train_days=66, oos_days=14)
    plan = WalkForwardFoldPlan(experiment_id="e1", folds=(fold0, fold1))

    result = compute_walk_forward_fold_geometry(experiment_id="e1", plan=plan)

    rows = result.to_dicts()
    assert rows[1]["train_overlap_seconds_with_previous_fold"] == 45 * 86_400


def test_compute_walk_forward_fold_geometry_no_overlap_when_step_exceeds_train() -> None:
    fold0 = _fold(fold_index=0, train_start=_START, train_days=10, oos_days=5)
    fold1 = _fold(fold_index=1, train_start=_START + timedelta(days=20), train_days=10, oos_days=5)
    plan = WalkForwardFoldPlan(experiment_id="e1", folds=(fold0, fold1))

    result = compute_walk_forward_fold_geometry(experiment_id="e1", plan=plan)

    assert result.to_dicts()[1]["train_overlap_seconds_with_previous_fold"] == 0


def test_compute_walk_forward_stability_empty_folds() -> None:
    result = compute_walk_forward_stability(experiment_id="e1", folds=pl.DataFrame())
    assert result.height == 0
    assert result.columns == empty_walk_forward_stability_dataframe().columns


def test_compute_walk_forward_stability_matches_real_demo_numbers() -> None:
    """Values taken from the real demo-robustness-nq-half-year experiment's
    14 real folds -- checked against real data, not a synthetic guess."""
    oos_values = [
        16.75,
        -16.0,
        -381.25,
        245.0,
        225.75,
        -38.25,
        -51.25,
        348.25,
        -301.0,
        153.75,
        315.5,
        -511.25,
        -419.5,
        549.25,
    ]
    folds = pl.DataFrame(
        {
            "oos_net_pnl": [str(v) for v in oos_values],
            "train_net_pnl": [str(v) for v in oos_values],
        }
    )

    result = compute_walk_forward_stability(experiment_id="e1", folds=folds)

    rows = {row["metric"]: row for row in result.to_dicts()}
    assert rows["oos_net_pnl"]["schema_version"] == STABILITY_SCHEMA_VERSION
    assert rows["oos_net_pnl"]["fold_count"] == 14
    assert rows["oos_net_pnl"]["mean"] == pytest.approx(9.696428571428571)
    assert rows["oos_net_pnl"]["std"] == pytest.approx(320.30517567342997)
    assert rows["oos_net_pnl"]["min"] == pytest.approx(-511.25)
    assert rows["oos_net_pnl"]["max"] == pytest.approx(549.25)
    assert rows["oos_net_pnl"]["pct_profitable_folds"] == pytest.approx(0.5)
    assert rows["train_net_pnl"]["pct_profitable_folds"] is None
