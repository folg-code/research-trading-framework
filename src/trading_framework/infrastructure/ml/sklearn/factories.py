"""Lazy sklearn family factories. Import sklearn inside each factory only."""

from __future__ import annotations

import numpy as np

from trading_framework.research.predictive.errors import PredictiveExtraError
from trading_framework.research.predictive.estimators import (
    EstimatorSpec,
    FittedPredictiveEstimator,
    PredictiveEstimator,
)

_ML_EXTRA = "ml"


def _import_sklearn() -> object:
    import sklearn

    return sklearn


def _require_sklearn(family_id: str) -> None:
    try:
        _import_sklearn()
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_ML_EXTRA!r}; "
            f"install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


class _SklearnFamilyStub:
    """Placeholder until Wave 2 ships ``describe()`` / ``fit()`` adapters."""

    def __init__(self, spec: EstimatorSpec) -> None:
        self.spec = spec

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> FittedPredictiveEstimator:
        msg = f"{self.spec.family} adapter is not implemented yet"
        raise NotImplementedError(msg)


def create_ridge_estimator(spec: EstimatorSpec) -> PredictiveEstimator:
    _require_sklearn("sklearn.ridge")
    return _SklearnFamilyStub(spec)


def create_elastic_net_estimator(spec: EstimatorSpec) -> PredictiveEstimator:
    _require_sklearn("sklearn.elastic_net")
    return _SklearnFamilyStub(spec)


def create_logistic_estimator(spec: EstimatorSpec) -> PredictiveEstimator:
    _require_sklearn("sklearn.logistic")
    return _SklearnFamilyStub(spec)
