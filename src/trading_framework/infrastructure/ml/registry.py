"""Estimator family registry: family id -> extra name + lazy factory (D-S040-07)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec, PredictiveEstimator

FamilyFactory = Callable[[EstimatorSpec], PredictiveEstimator]


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


def resolve_estimator(spec: EstimatorSpec) -> PredictiveEstimator:
    """Resolve ``spec.family`` to an estimator.

    Unknown family ids raise ``PredictiveSpecError`` even when extras are
    installed. A registered family whose extra is missing raises
    ``PredictiveExtraError`` from inside the lazy factory.
    """
    registration = _REGISTRY.get(spec.family)
    if registration is None:
        msg = f"unknown estimator family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    return registration.factory(spec)


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
