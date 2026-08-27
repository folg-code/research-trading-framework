"""Lazy torch family factories. Import torch inside each factory only."""

from __future__ import annotations

from trading_framework.infrastructure.ml.torch.adapter import TorchFeedforwardAdapter
from trading_framework.research.predictive.errors import PredictiveExtraError
from trading_framework.research.predictive.estimators import EstimatorSpec, PredictiveEstimator
from trading_framework.research.predictive.preprocessing import PreprocessingSpec

_DL_EXTRA = "dl"


def _import_torch() -> object:
    import torch

    return torch


def _require_torch(family_id: str) -> None:
    try:
        _import_torch()
    except ImportError as extra_missing:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_DL_EXTRA!r}; "
            f"install with `uv sync --extra {_DL_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from extra_missing


def create_torch_feedforward_regressor(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    estimator = TorchFeedforwardAdapter(spec, preprocessing=preprocessing)
    _require_torch("torch.feedforward.regressor")
    return estimator


def create_torch_feedforward_classifier(
    spec: EstimatorSpec,
    *,
    preprocessing: PreprocessingSpec | None = None,
) -> PredictiveEstimator:
    estimator = TorchFeedforwardAdapter(spec, preprocessing=preprocessing)
    _require_torch("torch.feedforward.classifier")
    return estimator
