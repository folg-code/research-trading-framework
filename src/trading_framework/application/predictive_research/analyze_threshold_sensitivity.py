"""Score-threshold sensitivity report for one persisted Predictive Research run.

Sprint 058 T002 (Phase 16 increment 16C). Reads only persisted predictions --
never a fitted model blob -- and writes ``threshold_sensitivity.json`` beside
``metrics.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_threshold_sensitivity_path,
)
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.predictive.estimators import EstimatorSpec, TaskType
from trading_framework.research.predictive.threshold_sensitivity import (
    DEFAULT_THRESHOLD_GRID,
    ThresholdSensitivityReport,
    sweep_threshold_sensitivity,
)


class ThresholdSensitivityError(ValidationError):
    """Raised when a threshold-sensitivity sweep cannot be computed for a run."""


@dataclass(frozen=True, slots=True)
class AnalyzeThresholdSensitivityRequest:
    """Input for one run's score-threshold sensitivity sweep."""

    run_ref: PredictiveRunRef
    storage_root: Path
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLD_GRID
    persist: bool = True
    run_repository: PredictiveRunRepository | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeThresholdSensitivityResult:
    """Threshold sensitivity report plus the path it was written to, if persisted."""

    run_id: str
    report: ThresholdSensitivityReport
    output_path: Path | None


def analyze_threshold_sensitivity(
    request: AnalyzeThresholdSensitivityRequest,
) -> AnalyzeThresholdSensitivityResult:
    """Sweep classification + finance metrics over one run's pooled TEST predictions.

    Refuses a REGRESSION run with a named error: a probability threshold only
    has meaning for a classifier's ``y_proba`` output. A continuous
    forward-return prediction already has its one decision threshold recorded
    in ``metrics.json`` (``build_predictive_metrics_report``'s
    ``decision_threshold``) -- sweeping that is a different question this
    module does not answer.
    """
    run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
    envelope = run_repository.read(request.run_ref)
    spec = EstimatorSpec.from_dict(envelope.manifest.estimator_spec)
    if spec.task_type is not TaskType.CLASSIFICATION:
        msg = (
            "threshold sensitivity requires a CLASSIFICATION run (y_proba-based); "
            f"got task_type={spec.task_type.value!r} for family={spec.family!r}, "
            f"run_id={envelope.manifest.run_id!r}"
        )
        raise ThresholdSensitivityError(msg)
    predictions = envelope.predictions
    report = sweep_threshold_sensitivity(
        run_id=envelope.manifest.run_id,
        y_true=_float_column(predictions, "y_true"),
        y_proba=_float_column(predictions, "y_proba"),
        forward_return=_float_column(predictions, "forward_return"),
        thresholds=request.thresholds,
    )
    output_path: Path | None = None
    if request.persist:
        output_path = predictive_research_run_threshold_sensitivity_path(
            request.storage_root, envelope.manifest.run_id
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return AnalyzeThresholdSensitivityResult(
        run_id=envelope.manifest.run_id,
        report=report,
        output_path=output_path,
    )


def _float_column(frame: pl.DataFrame, name: str) -> np.ndarray:
    return np.asarray(frame.get_column(name).to_list(), dtype=np.float64)
