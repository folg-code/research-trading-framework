"""Tests for PromotedArtifactRepository (T005, ADR-0024 condition 5)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.infrastructure.storage.paths import promoted_artifact_dir
from trading_framework.research.datasets.promoted_artifact import (
    PROMOTED_ARTIFACT_SCHEMA_VERSION,
    PromotedArtifactManifest,
    PromotedArtifactRef,
    PromotedArtifactRepository,
)


def _manifest(*, artifact_fingerprint: str = "f" * 64) -> PromotedArtifactManifest:
    return PromotedArtifactManifest(
        schema_version=PROMOTED_ARTIFACT_SCHEMA_VERSION,
        artifact_fingerprint=artifact_fingerprint,
        run_fingerprint="a" * 64,
        dataset_fingerprint="d" * 64,
        fold_id=3,
        feature_output_refs=("feature-a:close", "feature-b:atr"),
        model_family="sklearn.ridge",
        format="numpy_parameter_file",
        format_version="v1",
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "alpha": 1.0},
        training_library="sklearn",
        training_library_version="1.6.0",
        created_at_utc=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )


_PAYLOAD = {
    "features": ["feature-a:close", "feature-b:atr"],
    "coefficients": [0.5, -0.25],
    "intercept": 0.1,
    "preprocessing": {
        "impute_median": [0.0, 0.0],
        "standardize_mean": [1.0, 2.0],
        "standardize_scale": [1.0, 1.0],
    },
}


def test_write_read_round_trips_on_tmp_path(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = _manifest()

    ref = repository.write(manifest, artifact_payload=_PAYLOAD)
    assert ref == PromotedArtifactRef(artifact_fingerprint=manifest.artifact_fingerprint)

    loaded = repository.read_manifest(ref)
    assert loaded == manifest


def test_second_write_raises_file_exists_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = _manifest()
    repository.write(manifest, artifact_payload=_PAYLOAD)

    with pytest.raises(FileExistsError):
        repository.write(manifest, artifact_payload=_PAYLOAD)


def test_read_manifest_succeeds_with_corrupt_payload(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = _manifest()
    ref = repository.write(manifest, artifact_payload=_PAYLOAD)

    artifact_dir = promoted_artifact_dir(storage_root, manifest.artifact_fingerprint)
    (artifact_dir / "artifact.json").write_text("{not valid json", encoding="utf-8")

    loaded = repository.read_manifest(ref)
    assert loaded == manifest


def test_store_directory_contains_exactly_two_files_no_registry_no_index(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = _manifest()
    repository.write(manifest, artifact_payload=_PAYLOAD)

    artifact_dir = promoted_artifact_dir(storage_root, manifest.artifact_fingerprint)
    entries = sorted(path.name for path in artifact_dir.iterdir())
    assert entries == ["artifact.json", "manifest.json"]


def test_write_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = PromotedArtifactManifest(
        schema_version="promoted_artifact.v0",
        artifact_fingerprint="f" * 64,
        run_fingerprint="a" * 64,
        dataset_fingerprint="d" * 64,
        fold_id=3,
        feature_output_refs=("feature-a:close",),
        model_family="sklearn.ridge",
        format="numpy_parameter_file",
        format_version="v1",
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN"]},
        estimator_spec={"family": "sklearn.ridge"},
        training_library="sklearn",
        training_library_version="1.6.0",
        created_at_utc=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    )
    from trading_framework.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.write(manifest, artifact_payload=_PAYLOAD)


def test_promoted_artifacts_root_matches_documented_layout(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    repository = PromotedArtifactRepository(storage_root)
    manifest = _manifest()
    repository.write(manifest, artifact_payload=_PAYLOAD)

    expected = (
        storage_root
        / "research"
        / "predictive_research"
        / "promoted"
        / manifest.artifact_fingerprint
    )
    assert expected.exists()
    assert (expected / "manifest.json").exists()
    assert (expected / "artifact.json").exists()
