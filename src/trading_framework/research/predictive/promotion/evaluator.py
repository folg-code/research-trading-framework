"""The pure-NumPy promoted-artifact evaluator (ADR-0029 §1, §5).

``load_promoted_artifact`` turns a manifest + parameter payload into a
``PromotedPredictor``: a closed-form NumPy evaluation of

    x := impute_median(features)                  # NaN -> fitted median
    z := (x - standardize_mean) / standardize_scale
    y := z @ coefficients + intercept
         and, for sklearn.logistic only, p := 1 / (1 + exp(-y))

Every refusal in this module happens **before** any of that arithmetic runs,
and none of them can be bypassed — there is no ``strict=False``, no
``allow_mismatch``, no environment variable anywhere in this API.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from trading_framework.research.predictive.errors import (
    PredictiveSpecError,
    PromotedArtifactFormatError,
)
from trading_framework.research.predictive.preprocessing import PreprocessingSpec
from trading_framework.research.predictive.promotion.parameters import (
    SUPPORTED_FORMAT_VERSIONS,
    PromotedArtifactParameters,
)
from trading_framework.research.predictive.promotion.preprocessing import FittedNumpyPreprocessor

#: sklearn.ridge / sklearn.elastic_net evaluate as a plain linear combination.
LINEAR_MODEL_FAMILIES = frozenset({"sklearn.ridge", "sklearn.elastic_net"})
#: sklearn.logistic additionally applies a sigmoid (ADR-0029 §1).
LOGISTIC_MODEL_FAMILIES = frozenset({"sklearn.logistic"})
#: The evaluator's own allow-list (D-S049-13). Duplicated from, and must stay
#: in sync with, ``research.datasets.promoted_artifact.MODEL_FAMILY_ALLOWLIST``
#: — not imported, because layering runs research/predictive -> research/datasets,
#: never the reverse (ADR-0029 §9).
MODEL_FAMILY_ALLOWLIST = LINEAR_MODEL_FAMILIES | LOGISTIC_MODEL_FAMILIES


@runtime_checkable
class PromotedPredictor(Protocol):
    """Structural contract every promoted family's evaluator satisfies."""

    def predict(self, features: object) -> np.ndarray: ...


class PromotedManifestLike(Protocol):
    """The manifest fields ``load_promoted_artifact`` needs.

    Structural, not the concrete ``research.datasets.promoted_artifact.
    PromotedArtifactManifest`` — this package must not import
    ``research.datasets`` (ADR-0029 §9). ``PromotedArtifactManifest`` already
    has exactly these attribute names, so it satisfies this protocol as-is.

    Declared as read-only properties, not plain mutable attributes, so a
    frozen dataclass (the manifest, and every test fixture) satisfies this
    Protocol structurally under mypy as well as at runtime.
    """

    @property
    def format_version(self) -> str: ...

    @property
    def model_family(self) -> str: ...

    @property
    def feature_output_refs(self) -> Sequence[str]: ...

    @property
    def preprocessing_spec(self) -> Mapping[str, object]: ...

    @property
    def artifact_fingerprint(self) -> str: ...


@dataclass(frozen=True, slots=True)
class _LinearPromotedPredictor:
    """Evaluates ``z @ coefficients + intercept`` with no sigmoid."""

    preprocessor: FittedNumpyPreprocessor
    coefficients: np.ndarray
    intercept: float

    def predict(self, features: object) -> np.ndarray:
        return self._linear_output(features)

    def _linear_output(self, features: object) -> np.ndarray:
        transformed = self.preprocessor.transform(features)
        return np.asarray(transformed @ self.coefficients + self.intercept, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class _LogisticPromotedPredictor:
    """Evaluates the decision function, the sigmoid probability, and the label.

    ``predict`` returns the class label (0.0 / 1.0), matching the ``y_pred``
    bar in ADR-0029 §6's table. ``decision_function`` and ``predict_proba``
    are exposed separately so Path A (Sprint 049 T010b) can assert the exact
    decision function and the ulp-bounded probability independently — the
    tolerance must never hide an error upstream of the sigmoid.
    """

    preprocessor: FittedNumpyPreprocessor
    coefficients: np.ndarray
    intercept: float

    def decision_function(self, features: object) -> np.ndarray:
        transformed = self.preprocessor.transform(features)
        return np.asarray(transformed @ self.coefficients + self.intercept, dtype=np.float64)

    def predict_proba(self, features: object) -> np.ndarray:
        z = self.decision_function(features)
        return np.asarray(1.0 / (1.0 + np.exp(-z)), dtype=np.float64)

    def predict(self, features: object) -> np.ndarray:
        z = self.decision_function(features)
        return np.where(z >= 0.0, 1.0, 0.0).astype(np.float64)


def load_promoted_artifact(
    manifest: PromotedManifestLike,
    payload: PromotedArtifactParameters,
) -> PromotedPredictor:
    """Build a ``PromotedPredictor`` from a manifest + parameter payload.

    Hard-fails, before any arithmetic, on (ADR-0029 §5):

    - an unknown ``format_version``,
    - a ``model_family`` outside the linear/logistic allow-list,
    - a ``preprocessing_spec`` step the evaluator does not implement,
    - a feature-count mismatch between the manifest and the payload.

    A *training-library* version difference is deliberately not checked here
    (ADR-0029 §5's relaxation) — a parameter file has no coupling to
    scikit-learn, so that guard lives at *promotion* time instead
    (``infrastructure/ml/promotion.py``).
    """
    fingerprint = manifest.artifact_fingerprint

    if manifest.format_version not in SUPPORTED_FORMAT_VERSIONS:
        msg = (
            f"promoted artifact {fingerprint!r} has unsupported format_version "
            f"{manifest.format_version!r}; supported: {sorted(SUPPORTED_FORMAT_VERSIONS)}"
        )
        raise PromotedArtifactFormatError(msg)

    if manifest.model_family not in MODEL_FAMILY_ALLOWLIST:
        msg = (
            f"promoted artifact {fingerprint!r} has model_family "
            f"{manifest.model_family!r}, which is outside the evaluator's allow-list: "
            f"{sorted(MODEL_FAMILY_ALLOWLIST)}"
        )
        raise PromotedArtifactFormatError(msg)

    preprocessing_spec = _parse_preprocessing_spec(manifest.preprocessing_spec, fingerprint)

    n_features = len(manifest.feature_output_refs)
    _require_matching_feature_count(payload, n_features=n_features, fingerprint=fingerprint)

    preprocessor = FittedNumpyPreprocessor(
        spec=preprocessing_spec,
        impute_median=payload.impute_median,
        standardize_mean=payload.standardize_mean,
        standardize_scale=payload.standardize_scale,
    )
    coefficients = np.asarray(payload.coefficients, dtype=np.float64)

    if manifest.model_family in LOGISTIC_MODEL_FAMILIES:
        return _LogisticPromotedPredictor(
            preprocessor=preprocessor,
            coefficients=coefficients,
            intercept=payload.intercept,
        )
    return _LinearPromotedPredictor(
        preprocessor=preprocessor,
        coefficients=coefficients,
        intercept=payload.intercept,
    )


def _parse_preprocessing_spec(
    preprocessing_spec: Mapping[str, object],
    fingerprint: str,
) -> PreprocessingSpec:
    """Reuse ``PreprocessingSpec.from_dict``'s own step validation.

    The evaluator currently implements every step the domain
    ``PreprocessingStep`` enum declares (``IMPUTE_MEDIAN``, ``STANDARDIZE``),
    so "a step the evaluator does not implement" and "a step the domain enum
    does not declare" are the same failure today. Re-parsing through the
    domain type means a future third step is refused here automatically
    rather than silently accepted.
    """
    try:
        return PreprocessingSpec.from_dict(preprocessing_spec)
    except PredictiveSpecError as exc:
        msg = f"promoted artifact {fingerprint!r} has an unusable preprocessing_spec: {exc}"
        raise PromotedArtifactFormatError(msg) from exc


def _require_matching_feature_count(
    payload: PromotedArtifactParameters,
    *,
    n_features: int,
    fingerprint: str,
) -> None:
    stat_fields = {
        "coefficients": payload.coefficients,
        "impute_median": payload.impute_median,
        "standardize_mean": payload.standardize_mean,
        "standardize_scale": payload.standardize_scale,
    }
    for name, values in stat_fields.items():
        if values is not None and len(values) != n_features:
            msg = (
                f"promoted artifact {fingerprint!r} has a feature-count mismatch: "
                f"manifest declares {n_features} feature(s), payload {name!r} has "
                f"{len(values)}"
            )
            raise PromotedArtifactFormatError(msg)
