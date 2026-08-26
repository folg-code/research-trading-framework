"""Lazy LightGBM family factories. Import lightgbm inside each factory only."""

from __future__ import annotations

from trading_framework.infrastructure.ml.trees.lightgbm.adapter import LightGBMPredictiveEstimator
from trading_framework.research.predictive.errors import PredictiveExtraError
from trading_framework.research.predictive.estimators import EstimatorSpec, PredictiveEstimator
from trading_framework.research.predictive.preprocessing import PreprocessingSpec

_TREES_EXTRA = "ml-trees"


def _import_lightgbm() -> object:
    import lightgbm

    return lightgbm


def _require_lightgbm(family_id: str) -> None:
    try:
        _import_lightgbm()
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_TREES_EXTRA!r}; "
            f"install with `uv sync --extra {_TREES_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


def create_lightgbm_regressor(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_lightgbm("lightgbm.regressor")
    return LightGBMPredictiveEstimator(spec, preprocessing=preprocessing)


def create_lightgbm_classifier(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    _require_lightgbm("lightgbm.classifier")
    return LightGBMPredictiveEstimator(spec, preprocessing=preprocessing)
