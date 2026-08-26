"""Extra-free tests for analyze_predictive_run."""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import trading_framework
from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    AnalyzePredictiveRunRequest,
    RunPredictiveResearchRequest,
    analyze_predictive_run,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_metrics_path,
    predictive_research_run_model_path,
)
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.datasets.predictive_run import PredictiveRunRef
from trading_framework.research.predictive import (
    EstimatorDescription,
    EstimatorSpec,
    MetricSource,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_RUN_IMPL = __import__(
    "trading_framework.application.predictive_research.run_predictive_research",
    fromlist=["run_predictive_research"],
)


class _RecordingFitted:
    def predict(self, features: np.ndarray) -> np.ndarray:
        return np.full(features.shape[0], 0.25, dtype=np.float64)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        return None

    def describe(self) -> EstimatorDescription:
        return EstimatorDescription(
            library="testlib", version="0.0", resolved_params={"alpha": 1.0}
        )


class _ClassificationFitted:
    def predict(self, features: np.ndarray) -> np.ndarray:
        return np.ones(features.shape[0], dtype=np.float64)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        n_rows = features.shape[0]
        return np.column_stack(
            [np.full(n_rows, 0.25, dtype=np.float64), np.full(n_rows, 0.75, dtype=np.float64)]
        )

    def describe(self) -> EstimatorDescription:
        return EstimatorDescription(library="testlib", version="0.0", resolved_params={"C": 1.0})


class _RecordingEstimator:
    def __init__(self, fitted: _RecordingFitted | _ClassificationFitted | None = None) -> None:
        self._fitted: _RecordingFitted | _ClassificationFitted = fitted or _RecordingFitted()

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> _RecordingFitted | _ClassificationFitted:
        return self._fitted


def _labelled_rows(count: int = 40, *, binary: bool = False) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    returns = [0.01 + (index * 0.001) for index in range(count)]
    labels = [1.0 if index % 2 else 0.0 for index in range(count)] if binary else returns
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [1.0 + (index * 0.1) for index in range(count)],
            "label": labels,
            "forward_return": returns,
            "outcome_status": ["COMPLETE"] * count,
        },
        schema={
            "entity_id": pl.String(),
            "horizon_bars": pl.Int64(),
            "detected_at": _UTC_US,
            "available_at": _UTC_US,
            "label_end_at": _UTC_US,
            "atr_14": pl.Float64(),
            "label": pl.Float64(),
            "forward_return": pl.Float64(),
            "outcome_status": pl.String(),
        },
    )


def _write_dataset(
    storage_root: Path,
    *,
    dataset_id: str = "0123456789abcdef",
    label_kind: str = "REGRESSION",
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(
        _labelled_rows(binary=label_kind == "BINARY"),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )
    envelope = PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id=dataset_id,
            study_spec={
                "study_id": "atr_forward_return",
                "label": {"kind": label_kind, "horizon": "5m"},
            },
            definition_hash="a" * 64,
            dataset_fingerprint=dataset_id + ("b" * 48),
            source_dataset_ref="ES.c.0|ohlcv|1m|csv|test@1",
            time_range_start=datetime(2024, 1, 1, tzinfo=UTC),
            time_range_end=datetime(2024, 1, 2, tzinfo=UTC),
            exclusion_counts={
                "candidate_rows": 40,
                "labelled_rows": 40,
                "incomplete_horizon": 0,
                "insufficient_data": 0,
                "null_features": 0,
            },
            fold_summary=fold_summary_from_features(features),
            framework_version=framework_version,
            created_at_utc=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        ),
        features=features,
        folds=resolve_fold_boundaries(features),
    )
    return PredictiveDatasetRepository(storage_root).write(envelope)


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    estimator: _RecordingEstimator,
    *,
    family: str = "sklearn.ridge",
) -> None:
    def fake_resolve(
        spec: EstimatorSpec,
        *,
        preprocessing: object = None,
    ) -> _RecordingEstimator:
        assert spec.family == family
        return estimator

    monkeypatch.setattr(_RUN_IMPL, "resolve_estimator", fake_resolve)
    monkeypatch.setattr(_RUN_IMPL, "dump_fitted_estimator", lambda _fitted: b"opaque-artifact")


def test_analyze_is_independently_callable_and_writes_per_fold_and_pooled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root)
    _install_fakes(monkeypatch, _RecordingEstimator())
    run = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=EstimatorSpec(
                family="sklearn.ridge",
                hyperparameters={"alpha": 1.0},
                seed=7,
                task_type=TaskType.REGRESSION,
            ),
            storage_root=storage_root,
            persist=True,
            clock=FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
        )
    )
    metrics_path = predictive_research_run_metrics_path(storage_root, run.run_id)
    metrics_path.unlink()
    assert not metrics_path.exists()

    result = analyze_predictive_run(
        AnalyzePredictiveRunRequest(
            run_ref=PredictiveRunRef(run_id=run.run_id),
            storage_root=storage_root,
        )
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert result.metrics_path == metrics_path
    assert payload.get("folds")
    assert payload.get("pooled")
    assert MetricSource.MODEL.value in payload["pooled"]
    assert MetricSource.CONSTANT_MEAN.value in payload["pooled"]
    assert MetricSource.RANDOM_PERMUTATION.value in payload["pooled"]
    for fold_sources in payload["folds"].values():
        assert MetricSource.MODEL.value in fold_sources
        assert MetricSource.CONSTANT_MEAN.value in fold_sources
        assert MetricSource.RANDOM_PERMUTATION.value in fold_sources


def test_analyze_does_not_load_model_blobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root)
    _install_fakes(monkeypatch, _RecordingEstimator())
    run = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=EstimatorSpec(
                family="sklearn.ridge",
                hyperparameters={"alpha": 1.0},
                seed=7,
                task_type=TaskType.REGRESSION,
            ),
            storage_root=storage_root,
            persist=True,
        )
    )
    for fold_id in set(run.envelope.predictions.get_column("fold_id").to_list()):
        blob_path = predictive_research_run_model_path(storage_root, run.run_id, int(fold_id))
        blob_path.unlink()

    result = analyze_predictive_run(
        AnalyzePredictiveRunRequest(
            run_ref=PredictiveRunRef(run_id=run.run_id),
            storage_root=storage_root,
        )
    )
    assert result.report.pooled[MetricSource.MODEL.value].statistical.mae is not None


def test_analyze_classification_finance_uses_forward_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root, label_kind="BINARY")
    _install_fakes(
        monkeypatch,
        _RecordingEstimator(_ClassificationFitted()),
        family="sklearn.logistic",
    )
    run = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=EstimatorSpec(
                family="sklearn.logistic",
                hyperparameters={"C": 1.0},
                seed=3,
                task_type=TaskType.CLASSIFICATION,
            ),
            storage_root=storage_root,
            persist=True,
        )
    )
    predictions = run.envelope.predictions
    y_true = predictions.get_column("y_true").to_list()
    forward_return = predictions.get_column("forward_return").to_list()
    assert y_true != forward_return
    finance = run.metrics.pooled[MetricSource.MODEL.value].finance
    selected_returns = [
        ret
        for proba, ret in zip(
            predictions.get_column("y_proba").to_list(),
            forward_return,
            strict=True,
        )
        if proba >= 0.5
    ]
    assert finance.mean_forward_return_selected == pytest.approx(
        sum(selected_returns) / len(selected_returns)
    )
    assert finance.mean_forward_return_all == pytest.approx(
        sum(forward_return) / len(forward_return)
    )
    assert MetricSource.MAJORITY_CLASS.value in run.metrics.pooled


def test_analyze_and_metrics_modules_do_not_import_joblib_or_sklearn() -> None:
    framework_root = Path(trading_framework.__file__).resolve().parent
    paths = (
        framework_root / "research" / "predictive" / "metrics.py",
        framework_root / "application" / "predictive_research" / "analyze_predictive_run.py",
    )
    imported: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
    assert not any(name == "joblib" or name.startswith("joblib.") for name in imported)
    assert not any(name == "sklearn" or name.startswith("sklearn.") for name in imported)
    assert "sklearn.metrics" not in imported
