"""Lazy CatBoost family factories. Import catboost inside each factory only."""

from __future__ import annotations

from trading_framework.infrastructure.ml.trees.catboost.adapter import CatBoostPredictiveEstimator
from trading_framework.research.predictive.errors import PredictiveExtraError
from trading_framework.research.predictive.estimators import EstimatorSpec, PredictiveEstimator
from trading_framework.research.predictive.preprocessing import PreprocessingSpec

_TREES_EXTRA = "ml-trees"


def _import_catboost() -> object:
    import catboost

    return catboost


def _require_catboost(family_id: str) -> None:
    try:
        _import_catboost()
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_TREES_EXTRA!r}; "
            f"install with `uv sync --extra {_TREES_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


def create_catboost_regressor(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_catboost("catboost.regressor")
    return CatBoostPredictiveEstimator(spec, preprocessing=preprocessing)


def create_catboost_classifier(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_catboost("catboost.classifier")
    return CatBoostPredictiveEstimator(spec, preprocessing=preprocessing)
