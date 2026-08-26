"""LightGBM and CatBoost adapter tests that require extras ml + ml-trees."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    TaskType,
)

pytest.importorskip("lightgbm")
pytest.importorskip("catboost")
pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml_trees

_REGRESSORS = ("lightgbm.regressor", "catboost.regressor")
_CLASSIFIERS = ("lightgbm.classifier", "catboost.classifier")


def _spec(family: str, task_type: TaskType, **hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family=family,
        hyperparameters=hyperparameters,
        seed=7,
        task_type=task_type,
    )


@pytest.mark.parametrize("family", _REGRESSORS)
def test_regressor_fit_predict_returns_none_proba(family: str) -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    fitted = resolve_estimator(
        _spec(family, TaskType.REGRESSION, n_estimators=20, max_depth=2)
    ).fit(features, target, None)
    predicted = fitted.predict(features)
    assert predicted.shape == (4,)
    assert fitted.predict_proba(features) is None


@pytest.mark.parametrize("family", _CLASSIFIERS)
def test_classifier_fit_predict_and_predict_proba(family: str) -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [10.0], [11.0], [12.0], [13.0]])
    target = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    fitted = resolve_estimator(
        _spec(family, TaskType.CLASSIFICATION, n_estimators=20, max_depth=2)
    ).fit(features, target, None)
    predicted = fitted.predict(features)
    proba = fitted.predict_proba(features)
    assert predicted.shape == (8,)
    assert proba is not None
    assert proba.shape[0] == 8
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, rtol=1e-5, atol=1e-5)


@pytest.mark.parametrize(
    ("family", "library"),
    (("lightgbm.regressor", "lightgbm"), ("catboost.regressor", "catboost")),
)
def test_describe_pins_single_thread(family: str, library: str) -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    extra_pins = {"n_jobs": 8} if library == "lightgbm" else {"thread_count": 8}
    spec = EstimatorSpec(
        family=family,
        hyperparameters={"n_estimators": 10, **extra_pins},
        seed=13,
        task_type=TaskType.REGRESSION,
    )
    description = resolve_estimator(spec).fit(features, target, None).describe()
    assert description.library == library
    params = dict(description.resolved_params)
    if library == "lightgbm":
        assert params.get("n_jobs") == 1 or params.get("num_threads") == 1
        assert params.get("deterministic") in {True, "true"}
    else:
        assert params.get("thread_count") == 1
        assert str(params.get("task_type", "CPU")).upper() == "CPU"
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert json.loads(canonical) == params


@pytest.mark.parametrize("family", _REGRESSORS)
def test_repeated_fit_is_byte_identical(family: str) -> None:
    features = np.array(
        [[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0]],
        dtype=np.float64,
    )
    target = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    spec = _spec(family, TaskType.REGRESSION, n_estimators=30, max_depth=2, learning_rate=0.1)
    first = resolve_estimator(spec).fit(features, target, None).predict(features)
    second = resolve_estimator(spec).fit(features, target, None).predict(features)
    np.testing.assert_allclose(first, second, rtol=0.0, atol=0.0)


def test_lightgbm_rejects_gpu_device() -> None:
    with pytest.raises(PredictiveSpecError, match="rejects GPU"):
        resolve_estimator(_spec("lightgbm.regressor", TaskType.REGRESSION, device_type="gpu"))


def test_lightgbm_rejects_non_gbdt_boosting() -> None:
    with pytest.raises(PredictiveSpecError, match="boosting_type"):
        resolve_estimator(_spec("lightgbm.regressor", TaskType.REGRESSION, boosting_type="dart"))


def test_catboost_rejects_gpu_task_type() -> None:
    spec = EstimatorSpec(
        family="catboost.regressor",
        hyperparameters={"task_type": "GPU"},
        seed=7,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="GPU"):
        resolve_estimator(spec)


def test_catboost_rejects_unknown_bootstrap() -> None:
    with pytest.raises(PredictiveSpecError, match="bootstrap_type"):
        resolve_estimator(
            _spec("catboost.regressor", TaskType.REGRESSION, bootstrap_type="Poisson")
        )


@pytest.mark.parametrize("family", _REGRESSORS)
def test_unknown_hyperparameter_is_spec_error(family: str) -> None:
    with pytest.raises(PredictiveSpecError, match="unknown hyperparameters"):
        resolve_estimator(_spec(family, TaskType.REGRESSION, not_a_param=1.0))


@pytest.mark.parametrize("family", _REGRESSORS)
def test_fit_rejects_purged_metadata(family: str) -> None:
    features = np.array([[0.0], [1.0]])
    target = np.array([0.0, 1.0])
    estimator = resolve_estimator(_spec(family, TaskType.REGRESSION, n_estimators=10))
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        estimator.fit(features, target, (FoldRole.TRAIN, FoldRole.PURGED))


@pytest.mark.parametrize("family", _CLASSIFIERS)
def test_classifier_rejects_ternary_labels(family: str) -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
    target = np.array([0, 1, 2, 0, 1, 2])
    with pytest.raises(PredictiveSpecError, match="binary classification only"):
        resolve_estimator(_spec(family, TaskType.CLASSIFICATION, n_estimators=10)).fit(
            features, target, None
        )


@pytest.mark.parametrize("family", _REGRESSORS)
def test_regressor_rejects_classification_task_type(family: str) -> None:
    spec = EstimatorSpec(
        family=family,
        hyperparameters={},
        seed=1,
        task_type=TaskType.CLASSIFICATION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type REGRESSION"):
        resolve_estimator(spec)


@pytest.mark.parametrize("family", _CLASSIFIERS)
def test_classifier_rejects_regression_task_type(family: str) -> None:
    spec = EstimatorSpec(
        family=family,
        hyperparameters={},
        seed=1,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type CLASSIFICATION"):
        resolve_estimator(spec)


def test_lightgbm_iterations_alias_maps_to_n_estimators() -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    description = (
        resolve_estimator(
            _spec("lightgbm.regressor", TaskType.REGRESSION, iterations=12, max_depth=2)
        )
        .fit(features, target, None)
        .describe()
    )
    assert description.resolved_params.get("n_estimators") == 12


def test_lightgbm_rejects_conflicting_count_aliases() -> None:
    with pytest.raises(PredictiveSpecError, match="only one of"):
        resolve_estimator(
            _spec(
                "lightgbm.regressor",
                TaskType.REGRESSION,
                n_estimators=10,
                iterations=12,
            )
        )


def test_catboost_depth_alias_maps_to_depth() -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    description = (
        resolve_estimator(
            _spec("catboost.regressor", TaskType.REGRESSION, n_estimators=10, max_depth=3)
        )
        .fit(features, target, None)
        .describe()
    )
    assert description.resolved_params.get("depth") == 3


def test_catboost_rejects_conflicting_depth_aliases() -> None:
    with pytest.raises(PredictiveSpecError, match="only one of"):
        resolve_estimator(_spec("catboost.regressor", TaskType.REGRESSION, max_depth=3, depth=4))


def test_catboost_does_not_write_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    resolve_estimator(
        _spec("catboost.regressor", TaskType.REGRESSION, n_estimators=10, max_depth=2)
    ).fit(features, target, None)
    assert not (tmp_path / "catboost_info").exists()


@pytest.mark.parametrize("family", _REGRESSORS)
def test_regressor_recovers_linear_signal(family: str) -> None:
    rng = np.random.default_rng(0)
    features = rng.normal(size=(200, 3))
    target = 2.5 * features[:, 0] - 1.25 * features[:, 1] + 0.02 * rng.normal(size=200)
    predicted = (
        resolve_estimator(
            _spec(family, TaskType.REGRESSION, n_estimators=50, max_depth=3, learning_rate=0.1)
        )
        .fit(features, target, None)
        .predict(features)
    )
    correlation = float(np.corrcoef(target, predicted)[0, 1])
    assert correlation > 0.85
