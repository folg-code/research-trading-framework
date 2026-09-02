"""Tests for the PromotedArtifactManifest / PromotedArtifactRef contracts (T003)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.promoted_artifact import (
    PROMOTED_ARTIFACT_SCHEMA_VERSION,
    PromotedArtifactManifest,
    PromotedArtifactRef,
)
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact
from trading_framework.research.predictive.promotion.parameters import (
    PromotedArtifactParameters,
)


def _manifest(**overrides: object) -> PromotedArtifactManifest:
    fields: dict[str, object] = {
        "schema_version": PROMOTED_ARTIFACT_SCHEMA_VERSION,
        "artifact_fingerprint": "f" * 64,
        "run_fingerprint": "a" * 64,
        "dataset_fingerprint": "d" * 64,
        "fold_id": 3,
        "feature_output_refs": ("feature-a:close", "feature-b:atr"),
        "model_family": "sklearn.ridge",
        "format": "numpy_parameter_file",
        "format_version": "v1",
        "preprocessing_spec": {"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        "estimator_spec": {"family": "sklearn.ridge", "alpha": 1.0},
        "training_library": "sklearn",
        "training_library_version": "1.6.0",
        "created_at_utc": datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
    }
    fields.update(overrides)
    return PromotedArtifactManifest(**fields)  # type: ignore[arg-type]


def test_manifest_round_trips_through_to_dict_and_from_dict() -> None:
    manifest = _manifest()
    restored = PromotedArtifactManifest.from_dict(manifest.to_dict())
    assert restored == manifest


def test_manifest_preserves_declared_feature_order() -> None:
    manifest = _manifest(feature_output_refs=("z:1", "a:2", "m:3"))
    restored = PromotedArtifactManifest.from_dict(manifest.to_dict())
    assert restored.feature_output_refs == ("z:1", "a:2", "m:3")


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "artifact_fingerprint",
        "run_fingerprint",
        "dataset_fingerprint",
        "fold_id",
        "features",
        "model_family",
        "format",
        "format_version",
        "preprocessing_spec",
        "estimator_spec",
        "training_library",
        "training_library_version",
        "created_at_utc",
    ],
)
def test_missing_required_field_is_validation_error_naming_the_field(field: str) -> None:
    payload = _manifest().to_dict()
    del payload[field]
    with pytest.raises(ValidationError, match=field):
        PromotedArtifactManifest.from_dict(payload)


def test_model_family_outside_allowlist_is_validation_error() -> None:
    with pytest.raises(ValidationError, match="model_family"):
        _manifest(model_family="xgboost.tree")


def test_promoted_artifact_ref_normalizes_and_rejects_empty() -> None:
    ref = PromotedArtifactRef(artifact_fingerprint="  " + "a" * 64 + "  ")
    assert ref.artifact_fingerprint == "a" * 64
    with pytest.raises(ValidationError):
        PromotedArtifactRef(artifact_fingerprint="   ")


def test_manifest_satisfies_the_evaluator_s_promoted_manifest_like_protocol() -> None:
    """The real PromotedArtifactManifest, not just the evaluator's test double.

    research/datasets legitimately imports research/predictive (never the
    reverse -- ADR-0029 Section 9), so this is the correct place to prove
    load_promoted_artifact's structural PromotedManifestLike Protocol
    actually accepts the concrete manifest type it is meant for, not only
    the ad-hoc _FakeManifest used by the evaluator's own unit tests.
    """
    manifest = _manifest()
    payload = PromotedArtifactParameters(
        coefficients=(1.0, -2.0),
        intercept=0.5,
        standardize_mean=(0.0, 0.0),
        standardize_scale=(1.0, 1.0),
    )

    predictor = load_promoted_artifact(manifest, payload)

    predicted = predictor.predict([[1.0, 1.0]])
    assert predicted[0] == 1.0 * 1.0 + 1.0 * -2.0 + 0.5
