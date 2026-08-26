"""LightGBM PredictiveEstimator adapter. Import lightgbm inside fit() only."""

from __future__ import annotations

import io
from collections.abc import Mapping
from typing import Any

import numpy as np

from trading_framework.infrastructure.ml.sklearn.preprocessing import (
    FittedSklearnPreprocessor,
    as_feature_matrix,
    fit_sklearn_preprocessor,
)
from trading_framework.infrastructure.ml.trees._guards import (
    array_importance_vector,
    as_lower_str,
    as_target_vector,
    json_stable_mapping,
    reject_non_train_metadata,
    reject_unknown_hyperparameters,
    require_binary_labels,
    unique_hyperparameter_alias,
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
    "lightgbm.regressor": TaskType.REGRESSION,
    "lightgbm.classifier": TaskType.CLASSIFICATION,
}
_ALLOWED_USER_KEYS = frozenset(
    {
        "n_estimators",
        "iterations",
        "num_boost_round",
        "max_depth",
        "learning_rate",
        "subsample",
        "bagging_fraction",
        "reg_lambda",
        "feature_fraction",
        "min_child_samples",
        "num_leaves",
        "min_split_gain",
    }
)
_OVERWRITE_KEYS = frozenset(
    {
        "n_jobs",
        "num_threads",
        "random_state",
        "verbosity",
        "deterministic",
        "force_row_wise",
        "boosting_type",
        "device",
        "device_type",
    }
)
_COUNT_ALIASES = ("n_estimators", "iterations", "num_boost_round")
_SUBSAMPLE_ALIASES = ("subsample", "bagging_fraction")


class LightGBMPredictiveEstimator:
    """Unfitted LightGBM family adapter selected by ``EstimatorSpec.family``."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> None:
        expected = _EXPECTED_TASK_TYPE.get(spec.family)
        if expected is None:
            msg = f"unsupported lightgbm family: {spec.family!r}"
            raise PredictiveSpecError(msg)
        if spec.task_type is not expected:
            msg = (
                f"estimator family {spec.family!r} requires task_type {expected.value}, "
                f"got {spec.task_type.value}"
            )
            raise PredictiveSpecError(msg)
        _reject_gpu_and_booster(spec.hyperparameters, family_id=spec.family)
        reject_unknown_hyperparameters(
            spec.hyperparameters,
            allowed=_ALLOWED_USER_KEYS | _OVERWRITE_KEYS,
            family_id=spec.family,
        )
        unique_hyperparameter_alias(spec.hyperparameters, _COUNT_ALIASES, family_id=spec.family)
        unique_hyperparameter_alias(spec.hyperparameters, _SUBSAMPLE_ALIASES, family_id=spec.family)
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
    ) -> FittedLightGBMEstimator:
        _require_lightgbm(self._spec.family)
        _require_sklearn(self._spec.family)
        matrix = as_feature_matrix(features)
        reject_non_train_metadata(sample_metadata, n_rows=matrix.shape[0])
        y = as_target_vector(target, n_rows=matrix.shape[0])
        if self._spec.task_type is TaskType.CLASSIFICATION:
            require_binary_labels(y, family_id=self._spec.family)
        preprocessor = fit_sklearn_preprocessor(self._preprocessing, matrix)
        transformed = preprocessor.transform(matrix)
        estimator = _build_lightgbm_estimator(self._spec)
        try:
            estimator.fit(transformed, y)
        except (TypeError, ValueError) as exc:
            msg = f"lightgbm estimator {self._spec.family!r} failed to fit: {exc}"
            raise PredictiveSpecError(msg) from exc
        return FittedLightGBMEstimator(
            spec=self._spec,
            estimator=estimator,
            preprocessor=preprocessor,
            n_features=int(transformed.shape[1]),
        )


class FittedLightGBMEstimator:
    """Fitted LightGBM pipeline: fold-local preprocess then booster."""

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
            msg = f"lightgbm estimator {self._spec.family!r} failed to predict: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(predicted)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        if self._spec.task_type is not TaskType.CLASSIFICATION:
            return None
        transformed = self._preprocessor.transform(features)
        try:
            probabilities = self._estimator.predict_proba(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"lightgbm estimator {self._spec.family!r} failed to predict_proba: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(probabilities, dtype=np.float64)

    def describe(self) -> EstimatorDescription:
        import lightgbm

        return EstimatorDescription(
            library="lightgbm",
            version=str(lightgbm.__version__),
            resolved_params=json_stable_mapping(self._estimator.get_params()),
        )

    def native_feature_importance(self) -> NativeFeatureImportance | None:
        booster = self._estimator.booster_
        gain = array_importance_vector(
            booster.feature_importance(importance_type="gain"),
            n_features=self._n_features,
        )
        split = array_importance_vector(
            booster.feature_importance(importance_type="split"),
            n_features=self._n_features,
        )
        return NativeFeatureImportance(
            feature_names=tuple(f"f{index}" for index in range(self._n_features)),
            gain=gain,
            split=split,
        )

    def serialize_artifact(self) -> bytes:
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


def _require_lightgbm(family_id: str) -> None:
    try:
        __import__("lightgbm")
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


def _build_lightgbm_estimator(spec: EstimatorSpec) -> Any:
    if spec.family == "lightgbm.regressor":
        from lightgbm import LGBMRegressor

        cls: Any = LGBMRegressor
    elif spec.family == "lightgbm.classifier":
        from lightgbm import LGBMClassifier

        cls = LGBMClassifier
    else:
        msg = f"unsupported lightgbm family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    pinned: dict[str, Any] = {
        key: value
        for key, value in spec.hyperparameters.items()
        if key in _ALLOWED_USER_KEYS and key not in _COUNT_ALIASES and key not in _SUBSAMPLE_ALIASES
    }
    n_estimators = unique_hyperparameter_alias(
        spec.hyperparameters, _COUNT_ALIASES, family_id=spec.family
    )
    if n_estimators is not None:
        pinned["n_estimators"] = n_estimators
    subsample = unique_hyperparameter_alias(
        spec.hyperparameters, _SUBSAMPLE_ALIASES, family_id=spec.family
    )
    if subsample is not None:
        pinned["subsample"] = subsample
    pinned.update(
        {
            "n_jobs": 1,
            "num_threads": 1,
            "random_state": spec.seed,
            "verbosity": -1,
            "deterministic": True,
            "force_row_wise": True,
            "boosting_type": "gbdt",
        }
    )
    try:
        return cls(**pinned)
    except (TypeError, ValueError) as exc:
        msg = f"invalid hyperparameters for {spec.family}: {exc}"
        raise PredictiveSpecError(msg) from exc


def _reject_gpu_and_booster(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    boosting = as_lower_str(hyperparameters.get("boosting_type"))
    if boosting is not None and boosting != "gbdt":
        msg = f"{family_id} rejects boosting_type {boosting!r}; only gbdt is allowed"
        raise PredictiveSpecError(msg)
    device = as_lower_str(hyperparameters.get("device"))
    device_type = as_lower_str(hyperparameters.get("device_type"))
    if device in {"gpu", "cuda"} or device_type in {"gpu", "cuda"}:
        msg = f"{family_id} rejects GPU device; CPU-only (D-S042-09)"
        raise PredictiveSpecError(msg)
