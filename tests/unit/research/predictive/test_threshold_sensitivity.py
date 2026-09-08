"""Unit tests for the score-threshold sensitivity sweep (Sprint 058 T002)."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.threshold_sensitivity import (
    DEFAULT_THRESHOLD_GRID,
    THRESHOLD_SENSITIVITY_SCHEMA_VERSION,
    ThresholdSensitivityReport,
    sweep_threshold_sensitivity,
)

_SEED = 11


def _synthetic_scores(n: int = 200) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(_SEED)
    y_proba = rng.uniform(0.0, 1.0, n)
    y_true = (y_proba + rng.normal(0.0, 0.15, n) > 0.5).astype(np.float64)
    forward_return = (y_proba - 0.5) * 2.0 + rng.normal(0.0, 0.1, n)
    return y_true, y_proba, forward_return


def test_sweep_produces_one_point_per_threshold_in_order() -> None:
    y_true, y_proba, forward_return = _synthetic_scores()
    thresholds = (0.2, 0.5, 0.8)

    report = sweep_threshold_sensitivity(
        run_id="deadbeefcafebabe",
        y_true=y_true,
        y_proba=y_proba,
        forward_return=forward_return,
        thresholds=thresholds,
    )

    assert report.schema_version == THRESHOLD_SENSITIVITY_SCHEMA_VERSION
    assert report.run_id == "deadbeefcafebabe"
    assert tuple(point.threshold for point in report.points) == thresholds


def test_default_threshold_grid_excludes_degenerate_endpoints() -> None:
    assert 0.0 not in DEFAULT_THRESHOLD_GRID
    assert 1.0 not in DEFAULT_THRESHOLD_GRID
    assert len(DEFAULT_THRESHOLD_GRID) == 19


def test_coverage_is_non_increasing_as_threshold_rises() -> None:
    """A higher probability threshold can only select the same or fewer rows."""
    y_true, y_proba, forward_return = _synthetic_scores()
    thresholds = tuple(sorted(DEFAULT_THRESHOLD_GRID))

    report = sweep_threshold_sensitivity(
        run_id="deadbeefcafebabe",
        y_true=y_true,
        y_proba=y_proba,
        forward_return=forward_return,
        thresholds=thresholds,
    )

    coverages = [point.finance.coverage for point in report.points]
    assert all(earlier >= later for earlier, later in pairwise(coverages))


def test_empty_thresholds_is_rejected() -> None:
    y_true, y_proba, forward_return = _synthetic_scores()

    with pytest.raises(ValidationError, match="thresholds must be non-empty"):
        sweep_threshold_sensitivity(
            run_id="deadbeefcafebabe",
            y_true=y_true,
            y_proba=y_proba,
            forward_return=forward_return,
            thresholds=(),
        )


def test_report_rejects_no_points_directly() -> None:
    with pytest.raises(ValidationError, match="at least one point"):
        ThresholdSensitivityReport(
            schema_version=THRESHOLD_SENSITIVITY_SCHEMA_VERSION,
            run_id="deadbeefcafebabe",
            points=(),
        )


def test_report_round_trips_through_dict() -> None:
    y_true, y_proba, forward_return = _synthetic_scores()

    report = sweep_threshold_sensitivity(
        run_id="deadbeefcafebabe",
        y_true=y_true,
        y_proba=y_proba,
        forward_return=forward_return,
        thresholds=(0.3, 0.6),
    )

    restored = ThresholdSensitivityReport.from_dict(report.to_dict())

    assert restored == report
