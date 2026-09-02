"""Load-time format and family guard (Sprint 049 T007, ADR-0029 Section 5).

``load_promoted_artifact`` refuses four things, always before any arithmetic,
with no bypass anywhere in its API. It deliberately does **not** refuse on a
training-library version difference -- that guard lives at promotion time
instead (``infrastructure/ml/promotion.py``).

The manifest fixture here (``_FakeManifest``) is a plain stand-in that
satisfies ``PromotedManifestLike`` structurally. It is not
``research.datasets.promoted_artifact.PromotedArtifactManifest`` on purpose:
``research/predictive/`` must not depend on ``research/datasets`` (ADR-0029
Section 9), and this test suite is exercising the evaluator's own guard, not
the manifest dataclass's constructor validation.
"""

from __future__ import annotations

import inspect

import pytest

from tests.unit.research.predictive._promoted_artifact_fixtures import _manifest
from trading_framework.research.predictive.errors import PromotedArtifactFormatError
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact
from trading_framework.research.predictive.promotion.parameters import (
    PromotedArtifactParameters,
)


def _payload(*, n_features: int = 2) -> PromotedArtifactParameters:
    return PromotedArtifactParameters(
        coefficients=tuple(float(i) for i in range(1, n_features + 1)),
        intercept=0.0,
        standardize_mean=tuple(0.0 for _ in range(n_features)),
        standardize_scale=tuple(1.0 for _ in range(n_features)),
    )


def test_unknown_format_version_is_refused_before_arithmetic() -> None:
    manifest = _manifest(format_version="v99", fingerprint="fp-abc")
    with pytest.raises(PromotedArtifactFormatError, match="v99") as excinfo:
        load_promoted_artifact(manifest, _payload())
    assert "fp-abc" in str(excinfo.value)


def test_model_family_outside_allowlist_is_refused() -> None:
    manifest = _manifest(model_family="xgboost.classifier", fingerprint="fp-tree")
    with pytest.raises(PromotedArtifactFormatError, match=r"xgboost\.classifier") as excinfo:
        load_promoted_artifact(manifest, _payload())
    assert "fp-tree" in str(excinfo.value)


def test_unimplemented_preprocessing_step_is_refused() -> None:
    manifest = _manifest(steps=("PCA",), fingerprint="fp-pca")
    with pytest.raises(PromotedArtifactFormatError, match="fp-pca"):
        load_promoted_artifact(manifest, _payload())


def test_feature_count_mismatch_between_manifest_and_payload_is_refused() -> None:
    manifest = _manifest(n_features=3, fingerprint="fp-mismatch")
    payload = _payload(n_features=2)
    with pytest.raises(PromotedArtifactFormatError, match="fp-mismatch") as excinfo:
        load_promoted_artifact(manifest, payload)
    assert "3" in str(excinfo.value)
    assert "2" in str(excinfo.value)


def test_load_promoted_artifact_has_no_bypass_parameter() -> None:
    """The guard cannot be disabled -- there is no flag to check at any call site."""
    signature = inspect.signature(load_promoted_artifact)
    assert set(signature.parameters) == {"manifest", "payload"}


def test_training_library_version_difference_does_not_refuse_load() -> None:
    """A training-library version mismatch is provenance-only and loads fine.

    ADR-0029 Section 5's deliberate relaxation: a parameter file has no
    coupling to scikit-learn, because scikit-learn is not involved in reading
    it, so the numbers mean the same thing under any scikit-learn version.
    The library-version guard that *does* matter runs once, at *promotion*
    time, before any blob is unpickled (infrastructure/ml/promotion.py,
    Sprint 049 T006b) -- not here.
    """
    trained_under_old_sklearn = _manifest(training_library_version="1.1.0")
    trained_under_new_sklearn = _manifest(training_library_version="1.5.2")

    old_predictor = load_promoted_artifact(trained_under_old_sklearn, _payload())
    new_predictor = load_promoted_artifact(trained_under_new_sklearn, _payload())

    assert old_predictor is not None
    assert new_predictor is not None
