"""CatBoost PredictiveEstimator adapter. Import catboost inside fit() only."""

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
    TaskType,
)
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    default_preprocessing_spec,
)

_ML_EXTRA = "ml"
_TREES_EXTRA = "ml-trees"
_EXPECTED_TASK_TYPE: Mapping[str, TaskType] = {
    "catboost.regressor": TaskType.REGRESSION,
    "catboost.classifier": TaskType.CLASSIFICATION,
}
_ALLOWED_BOOTSTRAP = frozenset({"bernoulli", "bayesian", "mvs"})
_ALLOWED_USER_KEYS = frozenset(
    {
        "n_estimators",
        "iterations",
        "num_boost_round",
        "max_depth",
        "depth",
        "learning_rate",
        "subsample",
        "reg_lambda",
        "l2_leaf_reg",
        "border_count",
        "bootstrap_type",
    }
)
_OVERWRITE_KEYS = frozenset(
    {
        "thread_count",
        "task_type",
        "random_seed",
        "random_state",
        "verbose",
        "logging_level",
        "allow_writing_files",
        "loss_function",
    }
)
_COUNT_ALIASES = ("n_estimators", "iterations", "num_boost_round")
_DEPTH_ALIASES = ("max_depth", "depth")
_L2_ALIASES = ("reg_lambda", "l2_leaf_reg")


class CatBoostPredictiveEstimator:
    """Unfitted CatBoost family adapter selected by ``EstimatorSpec.family``."""

    def __init__(
        self,
        spec: EstimatorSpec,
        *,
        preprocessing: PreprocessingSpec | None = None,
    ) -> None:
        expected = _EXPECTED_TASK_TYPE.get(spec.family)
        if expected is None:
            msg = f"unsupported catboost family: {spec.family!r}"
            raise PredictiveSpecError(msg)
        if spec.task_type is not expected:
            msg = (
                f"estimator family {spec.family!r} requires task_type {expected.value}, "
                f"got {spec.task_type.value}"
            )
            raise PredictiveSpecError(msg)
        _reject_gpu(spec.hyperparameters, family_id=spec.family)
        _reject_bootstrap(spec.hyperparameters, family_id=spec.family)
        reject_unknown_hyperparameters(
            spec.hyperparameters,
            allowed=_ALLOWED_USER_KEYS | _OVERWRITE_KEYS,
            family_id=spec.family,
        )
        unique_hyperparameter_alias(spec.hyperparameters, _COUNT_ALIASES, family_id=spec.family)
        unique_hyperparameter_alias(spec.hyperparameters, _DEPTH_ALIASES, family_id=spec.family)
        unique_hyperparameter_alias(spec.hyperparameters, _L2_ALIASES, family_id=spec.family)
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
    ) -> FittedCatBoostEstimator:
        _require_catboost(self._spec.family)
        _require_sklearn(self._spec.family)
        matrix = as_feature_matrix(features)
        reject_non_train_metadata(sample_metadata, n_rows=matrix.shape[0])
        y = as_target_vector(target, n_rows=matrix.shape[0])
        if self._spec.task_type is TaskType.CLASSIFICATION:
            require_binary_labels(y, family_id=self._spec.family)
        preprocessor = fit_sklearn_preprocessor(self._preprocessing, matrix)
        transformed = preprocessor.transform(matrix)
        estimator = _build_catboost_estimator(self._spec)
        try:
            estimator.fit(transformed, y)
        except (TypeError, ValueError) as exc:
            msg = f"catboost estimator {self._spec.family!r} failed to fit: {exc}"
            raise PredictiveSpecError(msg) from exc
        return FittedCatBoostEstimator(
            spec=self._spec,
            estimator=estimator,
            preprocessor=preprocessor,
        )


class FittedCatBoostEstimator:
    """Fitted CatBoost pipeline: fold-local preprocess then booster."""

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
            msg = f"catboost estimator {self._spec.family!r} failed to predict: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(predicted).reshape(-1)

    def predict_proba(self, features: np.ndarray) -> np.ndarray | None:
        if self._spec.task_type is not TaskType.CLASSIFICATION:
            return None
        transformed = self._preprocessor.transform(features)
        try:
            probabilities = self._estimator.predict_proba(transformed)
        except (TypeError, ValueError) as exc:
            msg = f"catboost estimator {self._spec.family!r} failed to predict_proba: {exc}"
            raise PredictiveSpecError(msg) from exc
        return np.asarray(probabilities, dtype=np.float64)

    def describe(self) -> EstimatorDescription:
        import catboost

        return EstimatorDescription(
            library="catboost",
            version=str(catboost.__version__),
            resolved_params=json_stable_mapping(self._estimator.get_params()),
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


def _require_catboost(family_id: str) -> None:
    try:
        __import__("catboost")
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


def _build_catboost_estimator(spec: EstimatorSpec) -> Any:
    if spec.family == "catboost.regressor":
        from catboost import CatBoostRegressor

        cls: Any = CatBoostRegressor
        loss_function = "RMSE"
    elif spec.family == "catboost.classifier":
        from catboost import CatBoostClassifier

        cls = CatBoostClassifier
        loss_function = "Logloss"
    else:
        msg = f"unsupported catboost family: {spec.family!r}"
        raise PredictiveSpecError(msg)
    pinned: dict[str, Any] = {
        key: value
        for key, value in spec.hyperparameters.items()
        if key in _ALLOWED_USER_KEYS
        and key not in _COUNT_ALIASES
        and key not in _DEPTH_ALIASES
        and key not in _L2_ALIASES
    }
    iterations = unique_hyperparameter_alias(
        spec.hyperparameters, _COUNT_ALIASES, family_id=spec.family
    )
    if iterations is not None:
        pinned["iterations"] = iterations
    depth = unique_hyperparameter_alias(spec.hyperparameters, _DEPTH_ALIASES, family_id=spec.family)
    if depth is not None:
        pinned["depth"] = depth
    l2_leaf_reg = unique_hyperparameter_alias(
        spec.hyperparameters, _L2_ALIASES, family_id=spec.family
    )
    if l2_leaf_reg is not None:
        pinned["l2_leaf_reg"] = l2_leaf_reg
    pinned.update(
        {
            "thread_count": 1,
            "task_type": "CPU",
            "random_seed": spec.seed,
            "verbose": False,
            "allow_writing_files": False,
            "loss_function": loss_function,
        }
    )
    try:
        return cls(**pinned)
    except (TypeError, ValueError) as exc:
        msg = f"invalid hyperparameters for {spec.family}: {exc}"
        raise PredictiveSpecError(msg) from exc


def _reject_gpu(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    task_type = as_lower_str(hyperparameters.get("task_type"))
    if task_type == "gpu":
        msg = f"{family_id} rejects task_type GPU; CPU-only (D-S042-09)"
        raise PredictiveSpecError(msg)


def _reject_bootstrap(hyperparameters: Mapping[str, Any], *, family_id: str) -> None:
    bootstrap = as_lower_str(hyperparameters.get("bootstrap_type"))
    if bootstrap is None:
        return
    if bootstrap not in _ALLOWED_BOOTSTRAP:
        msg = (
            f"{family_id} bootstrap_type must be one of "
            f"Bernoulli, Bayesian, MVS; got {hyperparameters.get('bootstrap_type')!r}"
        )
        raise PredictiveSpecError(msg)
