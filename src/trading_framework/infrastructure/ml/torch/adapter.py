"""Torch PredictiveEstimator adapter. Import torch inside fit() only."""

from __future__ import annotations

import io
from collections.abc import Mapping
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.torch._guards import (
    ResolvedTorchHyperparameters,
    reject_outer_test_early_stopping,
    reject_sequence_window_spec,
    resolve_feedforward_hyperparameters,
)
from trading_framework.infrastructure.ml.torch.preprocessing import (
    FittedNumpyPreprocessor,
    as_feature_matrix,
    as_sequence_windows,
    fit_numpy_preprocessor,
    transform_windows,
)
from trading_framework.infrastructure.ml.torch.training import (
    InnerTrainingResult,
    build_feedforward_module,
    forward_logits,
    refit_for_epochs,
    train_with_early_stopping,
)
from trading_framework.infrastructure.ml.trees._guards import (
    as_target_vector,
    json_stable_mapping,
    reject_non_train_metadata,
    require_binary_labels,
)
from trading_framework.research.predictive.errors import PredictiveExtraError, PredictiveSpecError
from trading_framework.research.predictive.estimators import (
    EstimatorDescription,
    EstimatorSpec,
    NativeFeatureImportance,
    TaskType,
)
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    default_preprocessing_spec,
)
from trading_framework.research.predictive.selection import (
    DEFAULT_INNER_VALIDATION_FRACTION,
    split_inner_train_validation,
)

_DL_EXTRA = "dl"
_EXPECTED_TASK_TYPE: Mapping[str, TaskType] = {
    "torch.feedforward.regressor": TaskType.REGRESSION,
    "torch.feedforward.classifier": TaskType.CLASSIFICATION,
}


class TorchFeedforwardAdapter:
    """Unfitted tabular torch family adapter selected by ``EstimatorSpec.family``."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> None:
        expected = _EXPECTED_TASK_TYPE.get(spec.family)
        if expected is None:
            msg = f"unsupported torch family: {spec.family!r}"
            raise PredictiveSpecError(msg)
        if spec.task_type is not expected:
            msg = (
                f"estimator family {spec.family!r} requires task_type {expected.value}, "
                f"got {spec.task_type.value}"
            )
            raise PredictiveSpecError(msg)
        self._resolved = resolve_feedforward_hyperparameters(
            spec.hyperparameters,
            family_id=spec.family,
            is_classification=spec.task_type is TaskType.CLASSIFICATION,
        )
        self._spec = spec
        if preprocessing is None:
            self._preprocessing = default_preprocessing_spec()
        else:
            self._preprocessing = preprocessing

    def fit(
        self,
        features: np.ndarray,
        target: np.ndarray,
        sample_metadata: object,
    ) -> FittedTorchEstimator:
        reject_sequence_window_spec(sample_metadata, family_id=self._spec.family)
        reject_outer_test_early_stopping(sample_metadata, self._spec.hyperparameters)
        _require_torch(self._spec.family)
        torch = _import_torch()
        matrix = as_feature_matrix(features)
        reject_non_train_metadata(sample_metadata, n_rows=matrix.shape[0])
        y = as_target_vector(target, n_rows=matrix.shape[0])
        classes: tuple[Any, Any] | None = None
        if self._spec.task_type is TaskType.CLASSIFICATION:
            require_binary_labels(y, family_id=self._spec.family)
            unique = np.unique(y)
            classes = (unique[0], unique[1])
            y_fit = np.asarray(y == unique[1], dtype=np.float64)
        else:
            y_fit = np.asarray(y, dtype=np.float64)
        preprocessor = fit_numpy_preprocessor(self._preprocessing, matrix)
        transformed = preprocessor.transform(matrix)
        n_features = int(transformed.shape[1])
        hidden_sizes = self._resolved.hidden_sizes
        if hidden_sizes is None:
            msg = f"{self._spec.family} is missing hidden_sizes"
            raise PredictiveSpecError(msg)

        def build_model(torch_module: Any) -> Any:
            return build_feedforward_module(
                torch_module,
                n_features=n_features,
                hidden_sizes=hidden_sizes,
                dropout=self._resolved.dropout,
            )

        inner_train, inner_val = split_inner_train_validation(
            transformed.shape[0],
            inner_validation_fraction=DEFAULT_INNER_VALIDATION_FRACTION,
        )
        _, inner_result = train_with_early_stopping(
            torch,
            x_train=transformed[inner_train],
            y_train=y_fit[inner_train],
            x_val=transformed[inner_val],
            y_val=y_fit[inner_val],
            resolved=self._resolved,
            task_type=self._spec.task_type,
            seed=self._spec.seed,
            build_model=build_model,
        )
        model = refit_for_epochs(
            torch,
            features=transformed,
            target=y_fit,
            resolved=self._resolved,
            task_type=self._spec.task_type,
            seed=self._spec.seed,
            epochs=inner_result.stopping_epoch,
            build_model=build_model,
        )
        return FittedTorchEstimator(
            spec=self._spec,
            resolved=self._resolved,
            model=model,
            preprocessor=preprocessor,
            inner_result=inner_result,
            classes=classes,
            lookback_bars=None,
        )


class FittedTorchEstimator:
    """Fitted tabular torch pipeline: fold-local numpy preprocess then module."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        resolved: ResolvedTorchHyperparameters,
        model: Any,
        preprocessor: FittedNumpyPreprocessor,
        inner_result: InnerTrainingResult,
        classes: tuple[Any, Any] | None,
        lookback_bars: int | None = None,
    ) -> None:
        self._spec = spec
        self._resolved = resolved
        self._model = model
        self._preprocessor = preprocessor
        self._inner_result = inner_result
        self._classes = classes
        self._lookback_bars = lookback_bars

    def predict(self, features: np.ndarray) -> np.ndarray:
        logits = self._logits(features)
        if self._classes is None:
            return logits
        positive = logits >= 0.0
        return np.asarray(np.where(positive, self._classes[1], self._classes[0]))

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        if self._classes is None:
            return None
        logits = self._logits(features)
        positive = 1.0 / (1.0 + np.exp(-logits))
        return np.column_stack((1.0 - positive, positive)).astype(np.float64)

    def describe(self) -> EstimatorDescription:
        torch = _import_torch()
        params = self._resolved.as_json_mapping()
        params["family"] = self._spec.family
        params["seed"] = self._spec.seed
        params["stopping_epoch"] = self._inner_result.stopping_epoch
        params["inner_train_loss"] = list(self._inner_result.train_loss)
        params["inner_validation_loss"] = list(self._inner_result.validation_loss)
        return EstimatorDescription(
            library="torch",
            version=str(torch.__version__),
            resolved_params=json_stable_mapping(params),
        )

    def native_feature_importance(self) -> NativeFeatureImportance | None:
        return None

    def preprocessing_statistics(self) -> dict[str, list[float]]:
        """Fold-local imputer/scaler statistics fitted on the ``fit()`` matrix."""
        return self._preprocessor.statistics()

    def serialize_artifact(self) -> bytes:
        """Opaque ``torch.save`` blob of module weights and numpy preprocessor."""
        torch = _import_torch()
        buffer = io.BytesIO()
        torch.save(
            {
                "family": self._spec.family,
                "state_dict": self._model.state_dict(),
                "preprocessor": self._preprocessor.statistics(),
                "stopping_epoch": self._inner_result.stopping_epoch,
            },
            buffer,
        )
        return buffer.getvalue()

    def _logits(self, features: np.ndarray) -> np.ndarray:
        _require_torch(self._spec.family)
        torch = _import_torch()
        if self._lookback_bars is None:
            transformed = self._preprocessor.transform(features)
        else:
            windows = as_sequence_windows(features, lookback_bars=self._lookback_bars)
            transformed = transform_windows(self._preprocessor, windows)
        return forward_logits(torch, self._model, transformed)


def _import_torch() -> Any:
    import torch

    return torch


def _require_torch(family_id: str) -> None:
    try:
        _import_torch()
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_DL_EXTRA!r}; "
            f"install with `uv sync --extra {_DL_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc
