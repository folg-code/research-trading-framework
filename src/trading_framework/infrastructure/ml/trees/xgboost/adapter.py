"""XGBoost PredictiveEstimator adapter. Import xgboost inside fit() only."""

from __future__ import annotations

import io
import json
from collections.abc import Mapping
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.sklearn.preprocessing import (
    FittedSklearnPreprocessor,
    as_feature_matrix,
    fit_sklearn_preprocessor,
)
from trading_framework.infrastructure.ml.trees._guards import (
    as_target_vector,
    named_importance_vector,
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

_ML_EXTRA = "ml"
_TREES_EXTRA = "ml-trees"
_EXPECTED_TASK_TYPE: Mapping[str, TaskType] = {
    "xgboost.regressor": TaskType.REGRESSION,
    "xgboost.classifier": TaskType.CLASSIFICATION,
}
_ALLOWED_USER_KEYS = frozenset(
    {
        "n_estimators",
        "max_depth",
        "learning_rate",
        "subsample",
        "colsample_bytree",
        "min_child_weight",
        "reg_lambda",
        "reg_alpha",
        "gamma",
    }
)
_OVERWRITE_KEYS = frozenset(
    {
        "nthread",
        "n_jobs",
        "tree_method",
        "device",
        "random_state",
        "verbosity",
        "predictor",
        "objective",
    }
)
_GPU_DEVICES = frozenset({"cuda", "gpu"})
_GPU_TREE_METHODS = frozenset({"gpu_hist", "gpu_exact"})
_GPU_PREDICTORS = frozenset({"gpu_predictor"})


class XGBoostPredictiveEstimator:
    """Unfitted XGBoost family adapter selected by ``EstimatorSpec.family``."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> None:
        expected = _EXPECTED_TASK_TYPE.get(spec.family)
        if expected is None:
            msg = f"unsupported xgboost family: {spec.family!r}"
            raise PredictiveSpecError(msg)
        if spec.task_type is not expected:
            msg = (
                f"estimator family {spec.family!r} requires task_type {expected.value}, "
                f"got {spec.task_type.value}"
            )
            raise PredictiveSpecError(msg)
        _reject_gpu_options(spec.hyperparameters, family_id=spec.family)
        _reject_unknown_hyperparameters(spec.hyperparameters, family_id=spec.family)
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
    ) -> FittedXGBoostEstimator:
        _require_xgboost(self._spec.family)
        _require_sklearn(self._spec.family)
        matrix = as_feature_matrix(features)
        reject_non_train_metadata(sample_metadata, n_rows=matrix.shape[0])
        y = as_target_vector(target, n_rows=matrix.shape[0])
        if self._spec.task_type is TaskType.CLASSIFICATION:
            require_binary_labels(y, family_id=self._spec.family)
        preprocessor = fit_sklearn_preprocessor(self._preprocessing, matrix)
        transformed = preprocessor.transform(matrix)
        estimator = _build_xgboost_estimator(self._spec)
        try:
            estimator.fit(transformed, y)
        except (TypeError, ValueError) as exc:
            msg = f"xgboost estimator {self._spec.family!r} failed to fit: {exc}"
            raise PredictiveSpecError(msg) from exc
        return FittedXGBoostEstimator(
            spec=self._spec,
            estimator=estimator,
            preprocessor=preprocessor,
            n_features=int(transformed.shape[1]),
        )


class FittedXGBoostEstimator:
    """Fitted XGBoost pipeline: fold-local preprocess then booster."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        estimator: Any,
        preprocessor: FittedSklearnPreprocessor,
        n_features: int,
    ) -> None:
        self._spec = spec
        self._estimator = estimator
        self._preprocessor = preprocessor
        self._n_features = n_features

    def predict(self, features: np.ndarray) -> np.ndarray:
        transformed = self._preprocessor.transform(features)
        try:
            predicted = self._estimator.predict(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"xgboost estimator {self._spec.family!r} failed to predict: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(predicted)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        if self._spec.task_type is not TaskType.CLASSIFICATION:
            return None
        transformed = self._preprocessor.transform(features)
        try:
            probabilities = self._estimator.predict_proba(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"xgboost estimator {self._spec.family!r} failed to predict_proba: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(probabilities, dtype=np.float64)

    def describe(self) -> EstimatorDescription:
        import xgboost

        return EstimatorDescription(
            library="xgboost",
            version=str(xgboost.__version__),
            resolved_params=_json_stable_mapping(self._estimator.get_params()),
        )

    def native_feature_importance(self) -> NativeFeatureImportance | None:
        booster = self._estimator.get_booster()
        gain = named_importance_vector(
            booster.get_score(importance_type="gain"),
            n_features=self._n_features,
        )
        split = named_importance_vector(
            booster.get_score(importance_type="weight"),
            n_features=self._n_features,
        )
        return NativeFeatureImportance(
            feature_names=tuple(f"f{index}" for index in range(self._n_features)),
            gain=gain,
            split=split,
        )

    def serialize_artifact(self) -> bytes:
        """Opaque joblib blob of library objects only (D-S042-16)."""
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


def _require_xgboost(family_id: str) -> None:
    try:
        __import__("xgboost")
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_TREES_EXTRA!r}; "
            f"install with `uv sync --extra {_TREES_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


def _require_sklearn(family_id: str) -> None:
    try:
        __import__("sklearn")
    except ImportError as exc:
        msg = (
            f"estimator family {family_id!r} requires optional extra {_ML_EXTRA!r} "
            f"for fold-local preprocessing; install with `uv sync --extra {_ML_EXTRA}`"
        )
        raise PredictiveExtraError(msg) from exc


def _build_xgboost_estimator(spec: EstimatorSpec) -> Any:
    if spec.family == "xgboost.regressor":
        from xgboost import XGBRegressor

        cls: Any = XGBRegressor
        objective = "reg:squarederror"
    elif spec.family == "xgboost.classifier":
        from xgboost import XGBClassifier

        cls = XGBClassifier
        objective = "binary:logistic"
    else:
        msg = f"unsupported xgboost family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    pinned: dict[str, Any] = {
        key: value for key, value in spec.hyperparameters.items() if key in _ALLOWED_USER_KEYS
    }
    pinned.update(
        {
            "n_jobs": 1,
            "nthread": 1,
            "tree_method": "hist",
            "device": "cpu",
            "random_state": spec.seed,
            "verbosity": 0,
            "objective": objective,
        }
    )
    allowed = set(cls().get_params())
    constructor_kwargs = {key: value for key, value in pinned.items() if key in allowed}
    try:
        return cls(**constructor_kwargs)
    except (TypeError, ValueError) as exc:
        msg = f"invalid hyperparameters for {spec.family}: {exc}"
        raise PredictiveSpecError(msg) from exc


def _reject_gpu_options(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    device = _as_lower_str(hyperparameters.get("device"))
    if device in _GPU_DEVICES:
        msg = f"{family_id} rejects GPU device {device!r}; CPU-only (D-S042-09)"
        raise PredictiveSpecError(msg)
    tree_method = _as_lower_str(hyperparameters.get("tree_method"))
    if tree_method in _GPU_TREE_METHODS:
        msg = f"{family_id} rejects non-deterministic/GPU tree_method {tree_method!r}"
        raise PredictiveSpecError(msg)
    predictor = _as_lower_str(hyperparameters.get("predictor"))
    if predictor in _GPU_PREDICTORS:
        msg = f"{family_id} rejects GPU predictor {predictor!r}"
        raise PredictiveSpecError(msg)


def _reject_unknown_hyperparameters(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    allowed = _ALLOWED_USER_KEYS | _OVERWRITE_KEYS
    unknown = sorted(key for key in hyperparameters if key not in allowed)
    if unknown:
        msg = f"unknown hyperparameters for {family_id}: {unknown}"
        raise PredictiveSpecError(msg)


def _as_lower_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


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
            return None
        return value
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        converted = float(value)
        if not np.isfinite(converted):
            return None
        return converted
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [_json_stable_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_stable_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_stable_value(item) for item in value]
    return str(value)
