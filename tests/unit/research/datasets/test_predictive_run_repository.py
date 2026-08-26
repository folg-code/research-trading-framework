"""Tests for Predictive Research run repository round-trip."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

import trading_framework
from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_dir,
    predictive_research_run_model_path,
)
from trading_framework.research.datasets.predictive_run import (
    PREDICTIVE_RUN_SCHEMA_VERSION,
    PredictiveRunEnvelope,
    PredictiveRunManifest,
    PredictiveRunRef,
    PredictiveRunRepository,
    derive_predictive_run_id,
)


def _predictions() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "entity_id": ["a", "b", "c"],
            "fold_id": [0, 0, 1],
            "y_true": [0.1, 0.2, 1.0],
            "y_pred": [0.11, 0.18, 0.9],
            "y_proba": [None, None, None],
            "forward_return": [0.1, 0.2, 0.05],
        },
        schema={
            "entity_id": pl.String(),
            "fold_id": pl.Int64(),
            "y_true": pl.Float64(),
            "y_pred": pl.Float64(),
            "y_proba": pl.Float64(),
            "forward_return": pl.Float64(),
        },
    )


def _envelope(*, run_id: str = "0123456789abcdef") -> PredictiveRunEnvelope:
    return PredictiveRunEnvelope(
        manifest=PredictiveRunManifest(
            schema_version=PREDICTIVE_RUN_SCHEMA_VERSION,
            run_id=run_id,
            run_fingerprint=run_id + ("c" * 48),
            dataset_id="fedcba9876543210",
            dataset_fingerprint="d" * 64,
            estimator_spec={
                "family": "sklearn.ridge",
                "hyperparameters": {"alpha": 1.0},
                "seed": 7,
                "task_type": "REGRESSION",
            },
            preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
            library="sklearn",
            library_version="1.6.0",
            framework_version=framework_version,
            created_at_utc=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
            model_files={
                "0": "research/predictive_research/runs/0123456789abcdef/models/fold_0.bin",
                "1": "research/predictive_research/runs/0123456789abcdef/models/fold_1.bin",
            },
            estimator_description={
                "library": "sklearn",
                "version": "1.6.0",
                "resolved_params": {"alpha": 1.0},
            },
        ),
        predictions=_predictions(),
    )


def test_repository_write_read_round_trips_predictions_without_loading_blobs(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveRunRepository(storage_root)
    envelope = _envelope()
    blobs = {0: b"opaque-fold-0", 1: b"opaque-fold-1"}

    ref = repository.write(envelope, model_blobs=blobs)
    run_dir = predictive_research_run_dir(storage_root, envelope.manifest.run_id)
    assert ref == PredictiveRunRef(run_id=envelope.manifest.run_id)
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "predictions.parquet").exists()
    assert predictive_research_run_model_path(storage_root, envelope.manifest.run_id, 0).exists()
    assert predictive_research_run_model_path(storage_root, envelope.manifest.run_id, 1).exists()
    assert (
        predictive_research_run_model_path(storage_root, envelope.manifest.run_id, 0).read_bytes()
        == b"opaque-fold-0"
    )

    loaded = repository.read(ref)
    assert loaded.manifest.run_id == envelope.manifest.run_id
    assert loaded.manifest.run_fingerprint == envelope.manifest.run_fingerprint
    assert loaded.manifest.library == "sklearn"
    assert loaded.manifest.library_version == "1.6.0"
    assert loaded.manifest.estimator_spec["seed"] == 7
    assert_frame_equal(loaded.predictions, envelope.predictions, check_column_order=True)
    assert loaded.predictions.columns == [
        "entity_id",
        "fold_id",
        "y_true",
        "y_pred",
        "y_proba",
        "forward_return",
    ]


def test_repository_read_does_not_require_model_blobs(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveRunRepository(storage_root)
    envelope = _envelope()
    repository.write(envelope, model_blobs={0: b"blob-0", 1: b"blob-1"})
    for fold_id in (0, 1):
        predictive_research_run_model_path(storage_root, envelope.manifest.run_id, fold_id).unlink()

    loaded = repository.read(PredictiveRunRef(run_id=envelope.manifest.run_id))
    assert loaded.predictions.height == 3
    assert loaded.predictions.get_column("forward_return").to_list() == [0.1, 0.2, 0.05]


def test_repository_refuses_overwrite(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveRunRepository(storage_root)
    envelope = _envelope()
    repository.write(envelope, model_blobs={0: b"a", 1: b"b"})
    with pytest.raises(FileExistsError):
        repository.write(envelope, model_blobs={0: b"a", 1: b"b"})


def test_repository_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PredictiveRunRepository(storage_root)
    envelope = _envelope()
    bad_manifest = PredictiveRunManifest(
        schema_version="predictive_run.v0",
        run_id=envelope.manifest.run_id,
        run_fingerprint=envelope.manifest.run_fingerprint,
        dataset_id=envelope.manifest.dataset_id,
        dataset_fingerprint=envelope.manifest.dataset_fingerprint,
        estimator_spec=envelope.manifest.estimator_spec,
        preprocessing_spec=envelope.manifest.preprocessing_spec,
        library=envelope.manifest.library,
        library_version=envelope.manifest.library_version,
        framework_version=envelope.manifest.framework_version,
        created_at_utc=envelope.manifest.created_at_utc,
        model_files=envelope.manifest.model_files,
        estimator_description=envelope.manifest.estimator_description,
    )
    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.write(
            PredictiveRunEnvelope(manifest=bad_manifest, predictions=envelope.predictions),
            model_blobs={0: b"a", 1: b"b"},
        )


def test_derive_predictive_run_id_uses_fingerprint_prefix() -> None:
    fingerprint = "0123456789abcdef" + ("f" * 48)
    assert derive_predictive_run_id(fingerprint) == "0123456789abcdef"


def test_run_repository_module_does_not_import_joblib_or_sklearn() -> None:
    path = (
        Path(trading_framework.__file__).resolve().parent
        / "research"
        / "datasets"
        / "predictive_run.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)
    assert not any(name == "joblib" or name.startswith("joblib.") for name in imported)
    assert not any(name == "sklearn" or name.startswith("sklearn.") for name in imported)
