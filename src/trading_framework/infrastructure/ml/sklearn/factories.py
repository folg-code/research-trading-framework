"""Lazy sklearn family factories. Import sklearn inside each factory only."""

from __future__ import annotations

from trading_framework.infrastructure.ml.sklearn.adapter import SklearnPredictiveEstimator
from trading_framework.research.predictive.errors import PredictiveExtraError
from trading_framework.research.predictive.estimators import EstimatorSpec, PredictiveEstimator
from trading_framework.research.predictive.preprocessing import PreprocessingSpec

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


def create_ridge_estimator(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_sklearn("sklearn.ridge")
    return SklearnPredictiveEstimator(spec, preprocessing=preprocessing)


def create_elastic_net_estimator(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_sklearn("sklearn.elastic_net")
    return SklearnPredictiveEstimator(spec, preprocessing=preprocessing)


def create_logistic_estimator(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_sklearn("sklearn.logistic")
    return SklearnPredictiveEstimator(spec, preprocessing=preprocessing)
