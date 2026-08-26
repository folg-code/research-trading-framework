"""Estimator family registry: family id -> extra name + lazy factory (D-S040-07)."""

from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from trading_framework.research.predictive.errors import PredictiveExtraError, PredictiveSpecError
from trading_framework.research.predictive.estimators import (
    EstimatorSpec,
    FittedPredictiveEstimator,
    PredictiveEstimator,
)
from trading_framework.research.predictive.preprocessing import PreprocessingSpec

_ML_EXTRA = "ml"


class FamilyFactory(Protocol):
    """Lazy constructor selected by family id. Must not import sklearn at module import."""

    def __call__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> PredictiveEstimator: ...


@dataclass(frozen=True, slots=True)
class FamilyRegistration:
    """One estimator family: which extra it needs and how to construct it."""

    extra: str
    factory: FamilyFactory


_REGISTRY: dict[str, FamilyRegistration] = {}


def register_family(family_id: str, extra: str, factory: FamilyFactory) -> None:
    """Register a lazy factory for ``family_id``.

    The factory must import optional ML libraries inside the factory body, not
    at module import time.
    """
    normalized = family_id.strip()
    if not normalized:
        msg = "estimator family id must be non-empty"
        raise PredictiveSpecError(msg)
    extra_name = extra.strip()
    if not extra_name:
        msg = "estimator extra name must be non-empty"
        raise PredictiveSpecError(msg)
    if normalized in _REGISTRY:
        msg = f"estimator family already registered: {normalized!r}"
        raise PredictiveSpecError(msg)
    _REGISTRY[normalized] = FamilyRegistration(extra=extra_name, factory=factory)


def registered_families() -> Mapping[str, str]:
    """Return family id -> extra name for registered families."""
    return {family_id: registration.extra for family_id, registration in _REGISTRY.items()}


def resolve_estimator(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    """Resolve ``spec.family`` to an estimator.

    Unknown family ids raise ``PredictiveSpecError`` even when extras are
    installed. A registered family whose extra is missing raises
    ``PredictiveExtraError`` from inside the lazy factory.

    ``preprocessing`` is threaded into the adapter factory. Application code
    must not construct sklearn adapters directly.
    """
    registration = _REGISTRY.get(spec.family)
    if registration is None:
        msg = f"unknown estimator family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    return registration.factory(spec, preprocessing=preprocessing)


def dump_fitted_estimator(fitted: FittedPredictiveEstimator) -> bytes:
    """Serialize a fitted estimator as an opaque joblib blob (D-S040-17).

    Analysis must not ``joblib.load`` these bytes. Reproduce by re-fitting
    from the run manifest. Sklearn adapters dump estimator + preprocessor
    pipeline objects, not the Python wrapper (which holds unpicklable
    ``mappingproxy`` hyperparameters).
    """
    serialize = getattr(fitted, "serialize_artifact", None)
    if callable(serialize):
        return bytes(serialize())
    try:
        import joblib
    except ImportError as exc:
        msg = (
            f"serializing fitted estimators requires optional extra {_ML_EXTRA!r}; "
            f"install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc
    buffer = io.BytesIO()
    joblib.dump(fitted, buffer)
    return buffer.getvalue()


def _register_sklearn_families() -> None:
    from trading_framework.infrastructure.ml.sklearn.factories import (
        create_elastic_net_estimator,
        create_logistic_estimator,
        create_ridge_estimator,
    )

    register_family("sklearn.ridge", extra="ml", factory=create_ridge_estimator)
    register_family("sklearn.elastic_net", extra="ml", factory=create_elastic_net_estimator)
    register_family("sklearn.logistic", extra="ml", factory=create_logistic_estimator)


_register_sklearn_families()
