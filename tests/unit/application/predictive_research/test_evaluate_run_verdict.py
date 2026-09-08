"""Extra-free tests for evaluate_run_verdict (ADR-0032, S057-T004)."""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import trading_framework
from trading_framework import __version__ as framework_version
from trading_framework.application.predictive_research import (
    EvaluateRunVerdictRequest,
    RunPredictiveResearchRequest,
    evaluate_run_verdict,
    run_predictive_research,
)
from trading_framework.infrastructure.storage.paths import (
    predictive_research_dataset_dir,
    predictive_research_run_importance_path,
    predictive_research_run_metrics_path,
    predictive_research_run_verdict_path,
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
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    TaskType,
    assign_purged_walk_forward_folds,
)
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

    def native_feature_importance(self) -> object | None:
        return None


class _RecordingEstimator:
    def __init__(self, fitted: _RecordingFitted | None = None) -> None:
        self._fitted = fitted or _RecordingFitted()

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> _RecordingFitted:
        return self._fitted


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


def _write_dataset(
    storage_root: Path, *, dataset_id: str = "0123456789abcdef"
) -> PredictiveDatasetRef:
    features = assign_purged_walk_forward_folds(
        _labelled_rows(),
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
                "label": {"kind": "REGRESSION", "horizon": "5m"},
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


def _install_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_resolve(spec: EstimatorSpec, *, preprocessing: object = None) -> _RecordingEstimator:
        assert spec.family == "sklearn.ridge"
        return _RecordingEstimator()

    monkeypatch.setattr(_RUN_IMPL, "resolve_estimator", fake_resolve)
    monkeypatch.setattr(_RUN_IMPL, "dump_fitted_estimator", lambda _fitted: b"opaque-artifact")


def _build_run(storage_root: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    dataset_ref = _write_dataset(storage_root)
    _install_fakes(monkeypatch)
    result = run_predictive_research(
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
    return result.run_id


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): _hash_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_evaluate_writes_sidecar_with_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    run_id = _build_run(storage_root, monkeypatch)

    result = evaluate_run_verdict(
        EvaluateRunVerdictRequest(
            run_ref=PredictiveRunRef(run_id=run_id), storage_root=storage_root
        )
    )

    verdict_path = predictive_research_run_verdict_path(storage_root, run_id)
    assert result.verdict_path == verdict_path
    assert verdict_path.exists()

    payload = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert payload["rule_set_version"] == "verdict_rules.v1"
    assert payload["run_id"] == run_id
    assert payload["dataset_fingerprint"] == result.dataset_fingerprint
    assert payload["dataset_id"] == result.dataset_id
    assert payload["verdict"] == result.report.verdict.value
    assert isinstance(payload["facts"], dict)
    assert "pooled_model_primary" in payload["facts"]
    assert set(payload["facts"]["pooled_model_primary"]) == {"value", "source"}

    rule_ids = [entry["rule_id"] for entry in payload["rules"]]
    assert rule_ids == ["R2", "R3", "R4", "R1", "O1", "O2", "O3", "O4"]
    for entry in payload["rules"]:
        assert {
            "rule_id",
            "fired",
            "observed",
            "threshold",
            "source",
            "evaluated",
            "missing_input",
        } <= set(entry)


def test_reevaluating_same_run_produces_byte_identical_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    run_id = _build_run(storage_root, monkeypatch)
    request = EvaluateRunVerdictRequest(
        run_ref=PredictiveRunRef(run_id=run_id), storage_root=storage_root
    )

    evaluate_run_verdict(request)
    verdict_path = predictive_research_run_verdict_path(storage_root, run_id)
    first_bytes = verdict_path.read_bytes()

    evaluate_run_verdict(request)
    second_bytes = verdict_path.read_bytes()

    assert first_bytes == second_bytes


def test_evaluate_is_read_only_over_run_and_dataset_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    run_id = _build_run(storage_root, monkeypatch)

    manifest_path = (
        predictive_research_run_metrics_path(storage_root, run_id).parent / "manifest.json"
    )
    metrics_path = predictive_research_run_metrics_path(storage_root, run_id)
    importance_path = predictive_research_run_importance_path(storage_root, run_id)
    dataset_dir = predictive_research_dataset_dir(
        storage_root, json.loads(manifest_path.read_text(encoding="utf-8"))["dataset_id"]
    )

    before = {
        "manifest": _hash_file(manifest_path),
        "metrics": _hash_file(metrics_path),
        "importance": _hash_file(importance_path),
        "dataset": _hash_tree(dataset_dir),
    }

    evaluate_run_verdict(
        EvaluateRunVerdictRequest(
            run_ref=PredictiveRunRef(run_id=run_id), storage_root=storage_root
        )
    )

    after = {
        "manifest": _hash_file(manifest_path),
        "metrics": _hash_file(metrics_path),
        "importance": _hash_file(importance_path),
        "dataset": _hash_tree(dataset_dir),
    }
    assert before == after


def test_evaluate_does_not_open_model_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    run_id = _build_run(storage_root, monkeypatch)

    # Corrupt every persisted model blob: if evaluate_run_verdict ever tried to
    # deserialize one (joblib.load or otherwise), this would raise.
    run_dir = predictive_research_run_metrics_path(storage_root, run_id).parent
    models_dir = run_dir / "models"
    for blob_path in models_dir.glob("fold_*.bin"):
        blob_path.write_bytes(b"not-a-valid-serialized-estimator")
    blob_hashes_before = {path.name: _hash_file(path) for path in models_dir.glob("fold_*.bin")}

    result = evaluate_run_verdict(
        EvaluateRunVerdictRequest(
            run_ref=PredictiveRunRef(run_id=run_id), storage_root=storage_root
        )
    )

    assert result.verdict_path is not None
    blob_hashes_after = {path.name: _hash_file(path) for path in models_dir.glob("fold_*.bin")}
    assert blob_hashes_before == blob_hashes_after


def test_evaluate_run_verdict_module_does_not_import_joblib_or_sklearn() -> None:
    framework_root = Path(trading_framework.__file__).resolve().parent
    path = framework_root / "application" / "predictive_research" / "evaluate_run_verdict.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    assert not any(name == "joblib" or name.startswith("joblib.") for name in imported)
    assert not any(name == "sklearn" or name.startswith("sklearn.") for name in imported)


def test_evaluate_succeeds_and_verdict_unaffected_when_importance_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage_root = tmp_path / "workspace"
    run_id = _build_run(storage_root, monkeypatch)
    request = EvaluateRunVerdictRequest(
        run_ref=PredictiveRunRef(run_id=run_id), storage_root=storage_root
    )

    with_importance = evaluate_run_verdict(request)
    assert with_importance.verdict_path is not None
    payload_with = json.loads(with_importance.verdict_path.read_text(encoding="utf-8"))
    assert payload_with["facts"]["feature_importance_missing"]["value"] is None

    importance_path = predictive_research_run_importance_path(storage_root, run_id)
    importance_path.unlink()

    without_importance = evaluate_run_verdict(request)
    assert without_importance.verdict_path is not None
    payload_without = json.loads(without_importance.verdict_path.read_text(encoding="utf-8"))
    assert payload_without["facts"]["feature_importance_missing"]["value"] is not None
    assert payload_without["facts"]["feature_importance"]["value"] == {}

    # Absence of importance.json never changes the verdict: no rule reads it.
    assert without_importance.report.verdict == with_importance.report.verdict
