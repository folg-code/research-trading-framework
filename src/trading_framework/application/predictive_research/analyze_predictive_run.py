"""Analyze one persisted Predictive Research run — metrics over predictions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import predictive_research_run_metrics_path
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunEnvelope,
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.predictive.estimators import EstimatorSpec
from trading_framework.research.predictive.metrics import (
    PredictiveMetricsReport,
    build_predictive_metrics_report,
    fold_train_targets,
)


class AnalyzePredictiveRunError(ValidationError):
    """Raised when Predictive Research metrics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzePredictiveRunRequest:
    """Input for read-only metrics over one persisted Predictive Research run.

    Reads predictions and the labelled dataset (TRAIN statistics for reference
    baselines). Never deserializes fitted model blobs.
    """

    run_ref: PredictiveRunRef
    storage_root: Path
    decision_threshold: float | None = None
    persist: bool = True
    run_repository: PredictiveRunRepository | None = None
    dataset_repository: PredictiveDatasetRepository | None = None


@dataclass(frozen=True, slots=True)
class AnalyzePredictiveRunResult:
    """Metrics report for one Predictive Research run."""

    run_id: str
    report: PredictiveMetricsReport
    metrics_path: Path | None


def analyze_predictive_run(
    request: AnalyzePredictiveRunRequest,
) -> AnalyzePredictiveRunResult:
    """Load predictions, compute per-fold and pooled metrics, optionally persist.

    Does not call ``joblib.load`` or inspect ``models/fold_*.bin``. Reference
    baselines use TRAIN labels from the dataset envelope plus shuffled TEST
    predictions.
    """
    run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
    dataset_repository = request.dataset_repository or PredictiveDatasetRepository(
        request.storage_root
    )
    envelope = run_repository.read(request.run_ref)
    dataset = dataset_repository.read(PredictiveDatasetRef(dataset_id=envelope.manifest.dataset_id))
    report = metrics_report_from_envelopes(
        envelope,
        dataset.features,
        decision_threshold=request.decision_threshold,
    )
    metrics_path: Path | None = None
    if request.persist:
        metrics_path = write_predictive_metrics(
            request.storage_root,
            request.run_ref.run_id,
            report,
        )
    return AnalyzePredictiveRunResult(
        run_id=envelope.manifest.run_id,
        report=report,
        metrics_path=metrics_path,
    )


def metrics_report_from_envelopes(
    run_envelope: PredictiveRunEnvelope,
    labelled_features: pl.DataFrame,
    *,
    decision_threshold: float | None = None,
) -> PredictiveMetricsReport:
    """Build a metrics report from in-memory run predictions and TRAIN labels."""
    spec = EstimatorSpec.from_dict(run_envelope.manifest.estimator_spec)
    return build_predictive_metrics_report(
        run_envelope.predictions,
        train_targets_by_fold=fold_train_targets(labelled_features),
        task_type=spec.task_type,
        seed=spec.seed,
        run_id=run_envelope.manifest.run_id,
        decision_threshold=decision_threshold,
    )


def write_predictive_metrics(
    storage_root: Path,
    run_id: str,
    report: PredictiveMetricsReport,
) -> Path:
    """Write ``metrics.json`` next to ``predictions.parquet``."""
    path = predictive_research_run_metrics_path(storage_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path
