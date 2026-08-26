"""Extra-free tests for Predictive Research run orchestration."""

from __future__ import annotations

import ast
import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    RunPredictiveResearchRequest,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_dir,
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
from trading_framework.research.datasets.predictive_run import PredictiveRunRepository
from trading_framework.research.predictive import (
    EstimatorDescription,
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")
_RUN_IMPL = importlib.import_module(
    "trading_framework.application.predictive_research.run_predictive_research"
)


class _RecordingFitted:
    def predict(self, features: np.ndarray) -> np.ndarray:
        return np.full(features.shape[0], 0.25, dtype=np.float64)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        return None

    def describe(self) -> EstimatorDescription:
        return EstimatorDescription(
            library="testlib",
            version="0.0",
            resolved_params={"alpha": 1.0},
        )


class _RecordingEstimator:
    def __init__(self) -> None:
        self.fit_role_values: list[tuple[str, ...]] = []
        self.fit_row_counts: list[int] = []

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> _RecordingFitted:
        assert isinstance(sample_metadata, tuple)
        roles = tuple(
            role.value if isinstance(role, FoldRole) else str(role) for role in sample_metadata
        )
        self.fit_role_values.append(roles)
        self.fit_row_counts.append(int(features.shape[0]))
        return _RecordingFitted()


def _labelled_rows(count: int = 40) -> pl.DataFrame:
    start = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    timestamps = [start + timedelta(minutes=index) for index in range(count)]
    returns = [0.01 + (index * 0.001) for index in range(count)]
    return pl.DataFrame(
        {
            "entity_id": [timestamp.isoformat() for timestamp in timestamps],
            "horizon_bars": [5] * count,
            "detected_at": timestamps,
            "available_at": timestamps,
            "label_end_at": [timestamp + timedelta(minutes=5) for timestamp in timestamps],
            "atr_14": [1.0 + (index * 0.1) for index in range(count)],
            "label": returns,
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


def _assigned_features() -> pl.DataFrame:
    return assign_purged_walk_forward_folds(
        _labelled_rows(),
        PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("10m"),
            embargo_span=Timeframe("2m"),
            min_train_rows=5,
        ),
    )


def _write_dataset(
    storage_root: Path,
    *,
    dataset_id: str = "0123456789abcdef",
    label_kind: str = "REGRESSION",
) -> PredictiveDatasetRef:
    features = _assigned_features()
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


def _ridge_spec() -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    estimator: _RecordingEstimator,
) -> None:
    def fake_resolve(
        spec: EstimatorSpec,
        *,
        preprocessing: object = None,
    ) -> _RecordingEstimator:
        assert spec.family == "sklearn.ridge"
        assert preprocessing is not None
        return estimator

    monkeypatch.setattr(_RUN_IMPL, "resolve_estimator", fake_resolve)
    monkeypatch.setattr(_RUN_IMPL, "dump_fitted_estimator", lambda _fitted: b"opaque-artifact")


def test_run_writes_test_only_predictions_and_identical_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root)
    recorder = _RecordingEstimator()
    _install_fakes(monkeypatch, recorder)
    clock = FixedClock(datetime(2024, 7, 1, 12, 0, tzinfo=UTC))

    first = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=_ridge_spec(),
            storage_root=storage_root,
            persist=True,
            clock=clock,
        )
    )
    second = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_ref,
            estimator=_ridge_spec(),
            storage_root=storage_root,
            persist=False,
            clock=FixedClock(datetime(2024, 7, 2, 12, 0, tzinfo=UTC)),
        )
    )

    features = PredictiveDatasetRepository(storage_root).read(dataset_ref).features
    test_rows = features.filter(pl.col("fold_role") == FoldRole.TEST.value)
    predictions = first.envelope.predictions
    assert first.run_id == second.run_id
    assert first.fingerprint == second.fingerprint
    assert first.persisted is True
    assert second.persisted is False
    assert predictions.height == test_rows.height
    assert set(predictions.get_column("entity_id").to_list()) == set(
        test_rows.get_column("entity_id").to_list()
    )
    assert predictions.get_column("y_true").to_list() == test_rows.get_column("label").to_list()
    assert (
        predictions.get_column("forward_return").to_list()
        == test_rows.get_column("forward_return").to_list()
    )
    assert all(value is None for value in predictions.get_column("y_proba").to_list())
    assert FoldRole.PURGED.value not in {
        role for roles in recorder.fit_role_values for role in roles
    }
    assert FoldRole.EMBARGOED.value not in {
        role for roles in recorder.fit_role_values for role in roles
    }
    assert FoldRole.TEST.value not in {role for roles in recorder.fit_role_values for role in roles}
    assert all(roles and set(roles) == {FoldRole.TRAIN.value} for roles in recorder.fit_role_values)

    run_dir = predictive_research_run_dir(storage_root, first.run_id)
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "predictions.parquet").exists()
    assert not (run_dir / "metrics.json").exists()
    fold_ids = sorted(set(predictions.get_column("fold_id").to_list()))
    for fold_id in fold_ids:
        blob_path = predictive_research_run_model_path(storage_root, first.run_id, int(fold_id))
        assert blob_path.exists()
        assert blob_path.read_bytes() == b"opaque-artifact"

    loaded = PredictiveRunRepository(storage_root).read(first.run_ref)
    assert loaded.predictions.height == predictions.height
    assert loaded.manifest.library == "testlib"
    assert loaded.manifest.library_version == "0.0"


def test_run_rejects_ternary_datasets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_dataset(storage_root, label_kind="TERNARY")
    _install_fakes(monkeypatch, _RecordingEstimator())
    with pytest.raises(PredictiveSpecError, match="TERNARY"):
        run_predictive_research(
            RunPredictiveResearchRequest(
                dataset_ref=dataset_ref,
                estimator=EstimatorSpec(
                    family="sklearn.logistic",
                    hyperparameters={},
                    seed=1,
                    task_type=TaskType.CLASSIFICATION,
                ),
                storage_root=storage_root,
                persist=False,
            )
        )


def test_application_run_imports_registry_not_sklearn() -> None:
    assert _RUN_IMPL.__file__ is not None
    source = Path(_RUN_IMPL.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert "trading_framework.infrastructure.ml.registry" in imported
    assert "trading_framework.infrastructure.ml.sklearn" not in imported
    assert not any(name == "sklearn" or name.startswith("sklearn.") for name in imported)
    assert not any(name == "joblib" or name.startswith("joblib.") for name in imported)
    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in ("xgboost", "lightgbm", "catboost", "torch")
    )
