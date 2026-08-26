"""Sklearn PredictiveEstimator adapters. Import sklearn inside fit() only."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.sklearn.preprocessing import (
    FittedSklearnPreprocessor,
    as_feature_matrix,
    fit_sklearn_preprocessor,
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
    require_train_only_fit_roles,
)
from trading_framework.research.predictive.splitting import FoldRole

_ML_EXTRA = "ml"
_EXPECTED_TASK_TYPE: Mapping[str, TaskType] = {
    "sklearn.ridge": TaskType.REGRESSION,
    "sklearn.elastic_net": TaskType.REGRESSION,
    "sklearn.logistic": TaskType.CLASSIFICATION,
}
_BINARY_MULTI_CLASS = frozenset({None, "auto", "ovr"})


class SklearnPredictiveEstimator:
    """Unfitted sklearn family adapter selected by ``EstimatorSpec.family``."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> None:
        expected = _EXPECTED_TASK_TYPE.get(spec.family)
        if expected is None:
            msg = f"unsupported sklearn family: {spec.family!r}"
            raise PredictiveSpecError(msg)
        if spec.task_type is not expected:
            msg = (
                f"estimator family {spec.family!r} requires task_type {expected.value}, "
                f"got {spec.task_type.value}"
            )
            raise PredictiveSpecError(msg)
        if spec.family == "sklearn.logistic":
            multi_class = spec.hyperparameters.get("multi_class")
            if multi_class not in _BINARY_MULTI_CLASS:
                msg = "sklearn.logistic supports binary classification only"
                raise PredictiveSpecError(msg)
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
    ) -> FittedSklearnEstimator:
        _require_sklearn(self._spec.family)
        matrix = as_feature_matrix(features)
        _reject_non_train_metadata(sample_metadata, n_rows=matrix.shape[0])
        y = _as_target_vector(target, n_rows=matrix.shape[0])
        if self._spec.task_type is TaskType.CLASSIFICATION:
            _require_binary_labels(y)
        preprocessor = fit_sklearn_preprocessor(self._preprocessing, matrix)
        transformed = preprocessor.transform(matrix)
        estimator = _build_sklearn_estimator(self._spec)
        try:
            estimator.fit(transformed, y)
        except (TypeError, ValueError) as exc:
            msg = f"sklearn estimator {self._spec.family!r} failed to fit: {exc}"
            raise PredictiveSpecError(msg) from exc
        return FittedSklearnEstimator(
            spec=self._spec,
            estimator=estimator,
            preprocessor=preprocessor,
        )


class FittedSklearnEstimator:
    """Fitted sklearn pipeline: fold-local preprocess then estimator."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        estimator: Any,
        preprocessor: FittedSklearnPreprocessor,
    ) -> None:
        self._spec = spec
        self._estimator = estimator
        self._preprocessor = preprocessor

    def predict(self, features: np.ndarray) -> np.ndarray:
        transformed = self._preprocessor.transform(features)
        try:
            predicted = self._estimator.predict(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"sklearn estimator {self._spec.family!r} failed to predict: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(predicted)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        if self._spec.task_type is not TaskType.CLASSIFICATION:
            return None
        transformed = self._preprocessor.transform(features)
        try:
            probabilities = self._estimator.predict_proba(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"sklearn estimator {self._spec.family!r} failed to predict_proba: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(probabilities, dtype=np.float64)

    def describe(self) -> EstimatorDescription:
        import sklearn

        return EstimatorDescription(
            library="sklearn",
            version=str(sklearn.__version__),
            resolved_params=_json_stable_mapping(self._estimator.get_params()),
        )

    def native_feature_importance(self) -> NativeFeatureImportance | None:
        """Sklearn baselines do not expose tree-style native importance."""
        return None

    def preprocessing_statistics(self) -> dict[str, list[float]]:
        """Fold-local imputer/scaler statistics fitted on the ``fit()`` matrix."""
        return self._preprocessor.statistics()

    def serialize_artifact(self) -> bytes:
        """Opaque joblib blob of sklearn objects only (D-S040-17).

        ``EstimatorSpec`` stores hyperparameters as ``mappingproxy``, which
        pickle cannot serialize. The durable facts of a run are predictions;
        this blob is convenience, tagged with library name and version.
        """
        try:
            import joblib
        except ImportError as exc:
            msg = (
                f"serializing fitted estimators requires optional extra {_ML_EXTRA!r}; "
                f"install with `uv sync --extra {_ML_EXTRA}`"
            )
            raise PredictiveExtraError(msg) from exc
        buffer = io.BytesIO()
        joblib.dump(
            {
                "family": self._spec.family,
                "estimator": self._estimator,
                "preprocessor": self._preprocessor.pipeline(),
            },
            buffer,
        )
        return buffer.getvalue()


def _require_sklearn(family_id: str) -> None:
    try:
        __import__("sklearn")
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_ML_EXTRA!r}; "
            f"install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


def _build_sklearn_estimator(spec: EstimatorSpec) -> Any:
    if spec.family == "sklearn.ridge":
        from sklearn.linear_model import Ridge

        cls: Any = Ridge
    elif spec.family == "sklearn.elastic_net":
        from sklearn.linear_model import ElasticNet

        cls = ElasticNet
    elif spec.family == "sklearn.logistic":
        from sklearn.linear_model import LogisticRegression

        cls = LogisticRegression
    else:
        msg = f"unsupported sklearn family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    return _instantiate_with_pins(cls, spec)


def _instantiate_with_pins(cls: Any, spec: EstimatorSpec) -> Any:
    probe = cls()
    allowed = probe.get_params()
    pinned: dict[str, Any] = dict(spec.hyperparameters)
    if "random_state" in allowed:
        pinned["random_state"] = spec.seed
    if "n_jobs" in allowed:
        pinned["n_jobs"] = 1
    unknown = sorted(key for key in pinned if key not in allowed)
    if unknown:
        msg = f"unknown hyperparameters for {spec.family}: {unknown}"
        raise PredictiveSpecError(msg)
    try:
        return cls(**pinned)
    except (TypeError, ValueError) as exc:
        msg = f"invalid hyperparameters for {spec.family}: {exc}"
        raise PredictiveSpecError(msg) from exc


def _as_target_vector(target: object, *, n_rows: int) -> np.ndarray:
    array = np.squeeze(np.asarray(target))
    if array.ndim != 1:
        msg = "target must be 1-dimensional"
        raise PredictiveSpecError(msg)
    if array.shape[0] != n_rows:
        msg = f"target length {array.shape[0]} does not match feature rows {n_rows}"
        raise PredictiveSpecError(msg)
    if array.shape[0] == 0:
        msg = "target must be non-empty"
        raise PredictiveSpecError(msg)
    if np.issubdtype(array.dtype, np.number) and np.isnan(array.astype(np.float64)).any():
        msg = "target must not contain NaN"
        raise PredictiveSpecError(msg)
    return array


def _require_binary_labels(target: np.ndarray) -> None:
    classes = np.unique(target)
    if classes.size != 2:
        msg = (
            f"sklearn.logistic supports binary classification only; got {int(classes.size)} classes"
        )
        raise PredictiveSpecError(msg)


def _reject_non_train_metadata(sample_metadata: object, *, n_rows: int) -> None:
    roles = _fold_roles_from_metadata(sample_metadata)
    if roles is None:
        return
    if len(roles) != n_rows:
        msg = f"sample_metadata fold roles length {len(roles)} does not match feature rows {n_rows}"
        raise PredictiveSpecError(msg)
    require_train_only_fit_roles(roles)


def _fold_roles_from_metadata(sample_metadata: object) -> tuple[FoldRole, ...] | None:
    if sample_metadata is None:
        return None
    raw: object = sample_metadata
    if isinstance(sample_metadata, Mapping):
        if "fold_role" in sample_metadata:
            raw = sample_metadata["fold_role"]
        elif "fold_roles" in sample_metadata:
            raw = sample_metadata["fold_roles"]
        else:
            return None
    if isinstance(raw, np.ndarray):
        raw = raw.tolist()
    if isinstance(raw, (str, bytes)):
        return None
    if not isinstance(raw, Sequence):
        return None
    roles: list[FoldRole] = []
    for item in raw:
        if isinstance(item, FoldRole):
            roles.append(item)
            continue
        if isinstance(item, str):
            try:
                roles.append(FoldRole(item))
            except ValueError:
                return None
            continue
        return None
    return tuple(roles)


def _json_stable_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    converted = {str(key): _json_stable_value(value) for key, value in values.items()}
    try:
        canonical = json.dumps(converted, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        msg = "resolved estimator params must be JSON-serializable"
        raise PredictiveSpecError(msg) from exc
    loaded = json.loads(canonical)
    if not isinstance(loaded, dict):
        msg = "resolved estimator params must be a mapping"
        raise PredictiveSpecError(msg)
    return loaded


def _json_stable_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not np.isfinite(value):
            msg = "resolved estimator params must be JSON-serializable"
            raise PredictiveSpecError(msg)
        return value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_stable_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_stable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_stable_value(item) for item in value]
    return str(value)
