"""Tests for score-condition resolution (Sprint 058 T003, ADR-0033)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework.application.strategy_research import (
    ResolvedScoreCondition,
    ScoreConditionFamilyRefusedError,
    ScoreConditionNotFoundError,
    resolve_score_condition,
)
from trading_framework.infrastructure.storage.paths import promoted_artifact_manifest_path
from trading_framework.research.datasets.promoted_artifact import (
    PROMOTED_ARTIFACT_SCHEMA_VERSION,
    PromotedArtifactManifest,
    PromotedArtifactRepository,
)
from trading_framework.strategy import ScoreConditionSpec

_FINGERPRINT = "b" * 64


def _write_promoted_manifest(storage_root: Path, *, model_family: str) -> None:
    manifest = PromotedArtifactManifest(
        schema_version=PROMOTED_ARTIFACT_SCHEMA_VERSION,
        artifact_fingerprint=_FINGERPRINT,
        run_fingerprint="c" * 64,
        dataset_fingerprint="d" * 64,
        fold_id=3,
        feature_output_refs=("synthetic.signal_x|value|{}",),
        model_family=model_family,
        format="numpy_linear_v1",
        format_version="1",
        preprocessing_spec={"steps": ["impute_median", "standardize"]},
        estimator_spec={"family": model_family, "hyperparameters": {}, "seed": 7},
        training_library="scikit-learn",
        training_library_version="1.5.0",
        created_at_utc=datetime(2024, 7, 2, 9, 0, tzinfo=UTC),
    )
    PromotedArtifactRepository(storage_root).write(manifest, artifact_payload={"coefficients": []})


def _write_manifest_with_unlisted_family(storage_root: Path, *, fingerprint: str) -> None:
    """Bypass ``PromotedArtifactManifest``'s own construction-time allow-list
    guard by writing raw JSON directly -- the only way to produce a manifest
    naming a non-promotable family on disk, since promotion itself
    (ADR-0029 §1) already refuses to write one via the normal path. This is
    exactly the "hand-edited or corrupted manifest" scenario the family
    check defends against.
    """
    manifest_path = promoted_artifact_manifest_path(storage_root, fingerprint)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": PROMOTED_ARTIFACT_SCHEMA_VERSION,
                "artifact_fingerprint": fingerprint,
                "run_fingerprint": "c" * 64,
                "dataset_fingerprint": "d" * 64,
                "fold_id": 3,
                "features": ["synthetic.signal_x|value|{}"],
                "model_family": "xgboost.classifier",
                "format": "numpy_linear_v1",
                "format_version": "1",
                "preprocessing_spec": {"steps": ["impute_median", "standardize"]},
                "estimator_spec": {
                    "family": "xgboost.classifier",
                    "hyperparameters": {},
                    "seed": 7,
                },
                "training_library": "xgboost",
                "training_library_version": "3.0.0",
                "created_at_utc": datetime(2024, 7, 2, 9, 0, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def test_resolve_score_condition_succeeds_for_a_promotable_family(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    _write_promoted_manifest(storage_root, model_family="sklearn.logistic")
    spec = ScoreConditionSpec(artifact_fingerprint=_FINGERPRINT, threshold=0.6)

    resolved = resolve_score_condition(spec, storage_root=storage_root)

    assert isinstance(resolved, ResolvedScoreCondition)
    assert resolved.spec == spec
    assert resolved.manifest.artifact_fingerprint == _FINGERPRINT
    assert resolved.manifest.model_family == "sklearn.logistic"


def test_resolve_score_condition_refuses_a_missing_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    spec = ScoreConditionSpec(artifact_fingerprint="f" * 64, threshold=0.6)

    with pytest.raises(ScoreConditionNotFoundError, match="no promoted artifact found"):
        resolve_score_condition(spec, storage_root=storage_root)


def test_resolve_score_condition_refuses_a_non_allowlisted_family(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    fingerprint = "e" * 64
    _write_manifest_with_unlisted_family(storage_root, fingerprint=fingerprint)
    spec = ScoreConditionSpec(artifact_fingerprint=fingerprint, threshold=0.6)

    with pytest.raises(ScoreConditionFamilyRefusedError, match="outside the strategy-gate"):
        resolve_score_condition(spec, storage_root=storage_root)


def test_resolve_score_condition_refusal_names_the_offending_family(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    fingerprint = "e" * 64
    _write_manifest_with_unlisted_family(storage_root, fingerprint=fingerprint)
    spec = ScoreConditionSpec(artifact_fingerprint=fingerprint, threshold=0.6)

    with pytest.raises(ScoreConditionFamilyRefusedError, match=r"xgboost\.classifier"):
        resolve_score_condition(spec, storage_root=storage_root)
