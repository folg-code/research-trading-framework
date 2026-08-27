"""Sequence torch families (LSTM / GRU). Import torch inside fit() only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.torch._guards import (
    reject_outer_test_early_stopping,
    require_sequence_window_spec,
    resolve_sequence_hyperparameters,
)
from trading_framework.infrastructure.ml.torch.adapter import (
    FittedTorchEstimator,
    _import_torch,
    _require_torch,
)
from trading_framework.infrastructure.ml.torch.preprocessing import (
    as_feature_matrix,
    as_sequence_windows,
    fit_numpy_preprocessor,
    transform_windows,
)
from trading_framework.infrastructure.ml.torch.training import (
    build_recurrent_module,
    refit_for_epochs,
    train_with_early_stopping,
)
from trading_framework.infrastructure.ml.trees._guards import (
    as_target_vector,
    reject_non_train_metadata,
    require_binary_labels,
)
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec, TaskType
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    default_preprocessing_spec,
)
from trading_framework.research.predictive.selection import (
    DEFAULT_INNER_VALIDATION_FRACTION,
    split_inner_train_validation,
)

_EXPECTED_TASK_TYPE: Mapping[str, TaskType] = {
    "torch.lstm.regressor": TaskType.REGRESSION,
    "torch.lstm.classifier": TaskType.CLASSIFICATION,
    "torch.gru.regressor": TaskType.REGRESSION,
    "torch.gru.classifier": TaskType.CLASSIFICATION,
}
_CELL_BY_FAMILY: Mapping[str, str] = {
    "torch.lstm.regressor": "lstm",
    "torch.lstm.classifier": "lstm",
    "torch.gru.regressor": "gru",
    "torch.gru.classifier": "gru",
}


class TorchSequenceAdapter:
    """Unfitted rank-3 LSTM/GRU adapter selected by ``EstimatorSpec.family``."""

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
        cell = _CELL_BY_FAMILY[spec.family]
        self._resolved = resolve_sequence_hyperparameters(
            spec.hyperparameters,
            family_id=spec.family,
            cell=cell,
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
        window_spec = require_sequence_window_spec(sample_metadata, family_id=self._spec.family)
        reject_outer_test_early_stopping(sample_metadata, self._spec.hyperparameters)
        windows = as_sequence_windows(features, lookback_bars=window_spec.lookback_bars)
        reject_non_train_metadata(sample_metadata, n_rows=windows.shape[0])
        y = as_target_vector(target, n_rows=windows.shape[0])
        classes: tuple[Any, Any] | None = None
        if self._spec.task_type is TaskType.CLASSIFICATION:
            require_binary_labels(y, family_id=self._spec.family)
            unique = np.unique(y)
            classes = (unique[0], unique[1])
            y_fit = np.asarray(y == unique[1], dtype=np.float64)
        else:
            y_fit = np.asarray(y, dtype=np.float64)
        scaler_matrix = _require_scaler_features(sample_metadata, n_features=int(windows.shape[2]))
        _require_torch(self._spec.family)
        torch = _import_torch()
        preprocessor = fit_numpy_preprocessor(self._preprocessing, scaler_matrix)
        transformed = transform_windows(preprocessor, windows)
        hidden_size = self._resolved.hidden_size
        num_layers = self._resolved.num_layers
        cell = self._resolved.cell
        if hidden_size is None or num_layers is None or cell is None:
            msg = f"{self._spec.family} is missing sequence architecture fields"
            raise PredictiveSpecError(msg)
        n_features = int(transformed.shape[2])

        def build_model(torch_module: Any) -> Any:
            return build_recurrent_module(
                torch_module,
                cell=cell,
                n_features=n_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
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
            lookback_bars=window_spec.lookback_bars,
        )


def _require_scaler_features(sample_metadata: object, *, n_features: int) -> np.ndarray:
    """Fold-local scaler is fitted on 2d TRAIN rows, never on windowed 3d tensors."""
    if not isinstance(sample_metadata, Mapping):
        msg = "sequence family requires 2d TRAIN feature rows for the fold-local scaler"
        raise PredictiveSpecError(msg)
    raw = sample_metadata.get("scaler_features")
    if raw is None:
        raw = sample_metadata.get("feature_rows")
    if raw is None:
        msg = "sequence family requires 2d TRAIN feature rows for the fold-local scaler"
        raise PredictiveSpecError(msg)
    matrix = as_feature_matrix(raw)
    if matrix.shape[1] != n_features:
        msg = (
            f"scaler feature rows have {matrix.shape[1]} columns; "
            f"windows have {n_features} features"
        )
        raise PredictiveSpecError(msg)
    return matrix
