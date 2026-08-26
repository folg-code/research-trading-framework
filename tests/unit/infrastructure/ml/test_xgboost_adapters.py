"""XGBoost adapter tests that require extras ml + ml-trees."""

from __future__ import annotations

import json

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    TaskType,
)

pytest.importorskip("xgboost")
pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml_trees


def _regressor_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="xgboost.regressor",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _classifier_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="xgboost.classifier",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.CLASSIFICATION,
    )


def test_regressor_fit_predict_returns_none_proba() -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    fitted = resolve_estimator(_regressor_spec(n_estimators=20, max_depth=2)).fit(
        features, target, None
    )
    predicted = fitted.predict(features)
    assert predicted.shape == (4,)
    assert fitted.predict_proba(features) is None


def test_classifier_fit_predict_and_predict_proba() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [10.0], [11.0], [12.0], [13.0]])
    target = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    fitted = resolve_estimator(_classifier_spec(n_estimators=20, max_depth=2)).fit(
        features, target, None
    )
    predicted = fitted.predict(features)
    proba = fitted.predict_proba(features)
    assert predicted.shape == (8,)
    assert proba is not None
    assert proba.shape[0] == 8
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, rtol=1e-5, atol=1e-5)


def test_describe_captures_library_version_and_pinned_threads() -> None:
    import xgboost

    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    spec = EstimatorSpec(
        family="xgboost.regressor",
        hyperparameters={"n_estimators": 10, "n_jobs": 8, "random_state": 99},
        seed=13,
        task_type=TaskType.REGRESSION,
    )
    description = resolve_estimator(spec).fit(features, target, None).describe()
    assert description.library == "xgboost"
    assert description.version == xgboost.__version__
    params = dict(description.resolved_params)
    assert params.get("n_jobs") == 1 or params.get("nthread") == 1
    assert params["random_state"] == 13
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert json.loads(canonical) == params


def test_repeated_fit_is_byte_identical() -> None:
    features = np.array(
        [[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0]],
        dtype=np.float64,
    )
    target = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    spec = _regressor_spec(n_estimators=30, max_depth=2, learning_rate=0.1)
    first = resolve_estimator(spec).fit(features, target, None).predict(features)
    second = resolve_estimator(spec).fit(features, target, None).predict(features)
    np.testing.assert_array_equal(first, second)


def test_gpu_device_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="rejects GPU device"):
        resolve_estimator(_regressor_spec(device="cuda"))


def test_gpu_hist_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="tree_method"):
        resolve_estimator(_regressor_spec(tree_method="gpu_hist"))


def test_unknown_hyperparameter_is_spec_error() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown hyperparameters"):
        resolve_estimator(_regressor_spec(not_a_param=1.0))


def test_fit_rejects_purged_metadata() -> None:
    features = np.array([[0.0], [1.0]])
    target = np.array([0.0, 1.0])
    estimator = resolve_estimator(_regressor_spec(n_estimators=10))
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        estimator.fit(features, target, (FoldRole.TRAIN, FoldRole.PURGED))


def test_classifier_rejects_ternary_labels() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
    target = np.array([0, 1, 2, 0, 1, 2])
    with pytest.raises(PredictiveSpecError, match="binary classification only"):
        resolve_estimator(_classifier_spec(n_estimators=10)).fit(features, target, None)


def test_regressor_rejects_classification_task_type() -> None:
    spec = EstimatorSpec(
        family="xgboost.regressor",
        hyperparameters={},
        seed=1,
        task_type=TaskType.CLASSIFICATION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type REGRESSION"):
        resolve_estimator(spec)


def test_classifier_rejects_regression_task_type() -> None:
    spec = EstimatorSpec(
        family="xgboost.classifier",
        hyperparameters={},
        seed=1,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type CLASSIFICATION"):
        resolve_estimator(spec)


def test_regressor_recovers_linear_signal() -> None:
    rng = np.random.default_rng(0)
    features = rng.normal(size=(200, 3))
    target = 2.5 * features[:, 0] - 1.25 * features[:, 1] + 0.02 * rng.normal(size=200)
    predicted = (
        resolve_estimator(_regressor_spec(n_estimators=50, max_depth=3, learning_rate=0.1))
        .fit(features, target, None)
        .predict(features)
    )
    correlation = float(np.corrcoef(target, predicted)[0, 1])
    assert correlation > 0.9
