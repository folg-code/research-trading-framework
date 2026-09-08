"""Score-threshold sensitivity sweep for a classification predictive run.

Sprint 058 T002 (Phase 16 increment 16C): a probability threshold is chosen
out of sample, not by whichever value flattered the backtest -- sweeping the
statistical and finance-aware metrics across a threshold grid is what makes
that choice reviewable rather than implicit. This module computes the sweep
over already-scored predictions; it never fits, re-fits, or reads a fitted
model blob.

Library-free: numpy only, reusing the same ``classification_statistical_metrics``
/ ``finance_metrics`` functions ``build_predictive_metrics_report`` calls once
at a single declared threshold -- this module calls them repeatedly, at a grid
of thresholds, instead of duplicating their arithmetic.

A threshold only has meaning for a classifier's probability output
(``y_proba``). Refusing a REGRESSION run is the caller's job
(``application/predictive_research/analyze_threshold_sensitivity.py``), not
this module's -- this is a pure function over already-selected scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.metrics import (
    FinanceMetrics,
    StatisticalMetrics,
    classification_statistical_metrics,
    finance_metrics,
)

THRESHOLD_SENSITIVITY_SCHEMA_VERSION = "threshold_sensitivity.v1"

#: Deciles of [0, 1], excluding the degenerate 0.0/1.0 endpoints (an
#: all-select or all-reject threshold is not a useful gate).
DEFAULT_THRESHOLD_GRID: tuple[float, ...] = tuple(round(0.05 * step, 2) for step in range(1, 20))


@dataclass(frozen=True, slots=True)
class ThresholdSensitivityPoint:
    """Statistical and finance-aware metrics at one probability threshold."""

    threshold: float
    statistical: StatisticalMetrics
    finance: FinanceMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "statistical": self.statistical.to_dict(),
            "finance": self.finance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ThresholdSensitivityPoint:
        return cls(
            threshold=float(payload["threshold"]),
            statistical=StatisticalMetrics.from_dict(payload["statistical"]),
            finance=FinanceMetrics.from_dict(payload["finance"]),
        )


@dataclass(frozen=True, slots=True)
class ThresholdSensitivityReport:
    """A run's pooled TEST predictions, swept across a threshold grid.

    ``points`` is ordered exactly as ``thresholds`` was given to
    ``sweep_threshold_sensitivity`` -- callers choosing an out-of-sample
    cutoff read this sequentially, not by re-sorting.
    """

    schema_version: str
    run_id: str
    points: tuple[ThresholdSensitivityPoint, ...]

    def __post_init__(self) -> None:
        if not self.points:
            msg = "threshold sensitivity report must include at least one point"
            raise ValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "points": [point.to_dict() for point in self.points],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ThresholdSensitivityReport:
        return cls(
            schema_version=str(payload["schema_version"]),
            run_id=str(payload["run_id"]),
            points=tuple(ThresholdSensitivityPoint.from_dict(point) for point in payload["points"]),
        )


def sweep_threshold_sensitivity(
    *,
    run_id: str,
    y_true: np.ndarray,
    y_proba: np.ndarray,
    forward_return: np.ndarray,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLD_GRID,
) -> ThresholdSensitivityReport:
    """Sweep classification + finance metrics across a probability threshold grid.

    Pooled TEST rows only -- a diagnostic over one run's already-computed
    predictions, never a re-fit and never a second look at TRAIN.
    """
    if not thresholds:
        msg = "thresholds must be non-empty"
        raise ValidationError(msg)
    points = tuple(
        ThresholdSensitivityPoint(
            threshold=threshold,
            statistical=classification_statistical_metrics(y_true, y_proba, threshold=threshold),
            finance=finance_metrics(y_proba, forward_return, threshold=threshold),
        )
        for threshold in thresholds
    )
    return ThresholdSensitivityReport(
        schema_version=THRESHOLD_SENSITIVITY_SCHEMA_VERSION,
        run_id=run_id,
        points=points,
    )
