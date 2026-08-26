"""Sklearn adapter tests that require the optional ml extra."""

from __future__ import annotations

import json

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.infrastructure.ml.sklearn.adapter import (
    FittedSklearnEstimator,
    SklearnPredictiveEstimator,
)
from trading_framework.infrastructure.ml.sklearn.preprocessing import fit_sklearn_preprocessor
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    PreprocessingSpec,
    PreprocessingStep,
    TaskType,
    default_preprocessing_spec,
)

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml


def _ridge_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _elastic_net_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.elastic_net",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _logistic_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.logistic",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.CLASSIFICATION,
    )


def test_ridge_fit_predict_returns_none_proba() -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    fitted = resolve_estimator(_ridge_spec(alpha=1.0)).fit(features, target, None)
    predicted = fitted.predict(features)
    assert predicted.shape == (4,)
    assert fitted.predict_proba(features) is None


def test_elastic_net_fit_predict_returns_none_proba() -> None:
    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    fitted = resolve_estimator(_elastic_net_spec(alpha=0.5, l1_ratio=0.5)).fit(
        features, target, None
    )
    assert fitted.predict(features).shape == (4,)
    assert fitted.predict_proba(features) is None


def test_logistic_fit_predict_and_predict_proba() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [10.0], [11.0], [12.0], [13.0]])
    target = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    fitted = resolve_estimator(_logistic_spec(C=1.0)).fit(features, target, None)
    predicted = fitted.predict(features)
    proba = fitted.predict_proba(features)
    assert predicted.shape == (8,)
    assert proba is not None
    assert proba.shape == (8, 2)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0)


def test_describe_captures_library_version_and_resolved_params() -> None:
    import sklearn

    features = np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])
    target = np.array([0.0, 1.0, 2.0, 3.0])
    fitted = resolve_estimator(_ridge_spec(alpha=2.5)).fit(features, target, None)
    description = fitted.describe()
    assert description.library == "sklearn"
    assert description.version == sklearn.__version__
    assert description.resolved_params["alpha"] == 2.5
    payload = {
        "library": description.library,
        "version": description.version,
        "resolved_params": dict(description.resolved_params),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert json.loads(canonical) == payload


def test_logistic_pins_n_jobs_and_random_state_from_spec() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [10.0], [11.0]])
    target = np.array([0, 0, 0, 1, 1, 1])
    spec = EstimatorSpec(
        family="sklearn.logistic",
        hyperparameters={"C": 1.0, "n_jobs": 8, "random_state": 99},
        seed=13,
        task_type=TaskType.CLASSIFICATION,
    )
    description = resolve_estimator(spec).fit(features, target, None).describe()
    assert description.resolved_params["n_jobs"] == 1
    assert description.resolved_params["random_state"] == 13


def test_preprocessing_statistics_differ_across_train_slices() -> None:
    spec = default_preprocessing_spec()
    slice_a = np.array([[1.0, 10.0], [3.0, 30.0], [5.0, 50.0]])
    slice_b = np.array([[100.0, 200.0], [200.0, 400.0], [300.0, 600.0]])
    stats_a = fit_sklearn_preprocessor(spec, slice_a).statistics()
    stats_b = fit_sklearn_preprocessor(spec, slice_b).statistics()
    assert stats_a["impute_median"] != stats_b["impute_median"]
    assert stats_a["standardize_mean"] != stats_b["standardize_mean"]
    fitted_a = resolve_estimator(_ridge_spec()).fit(slice_a, np.array([1.0, 2.0, 3.0]), None)
    fitted_b = resolve_estimator(_ridge_spec()).fit(slice_b, np.array([1.0, 2.0, 3.0]), None)
    assert isinstance(fitted_a, FittedSklearnEstimator)
    assert isinstance(fitted_b, FittedSklearnEstimator)
    stats_fit_a = fitted_a.preprocessing_statistics()
    stats_fit_b = fitted_b.preprocessing_statistics()
    assert stats_fit_a["impute_median"] != stats_fit_b["impute_median"]
    assert stats_fit_a["standardize_mean"] != stats_fit_b["standardize_mean"]


def test_fit_rejects_purged_and_embargoed_metadata() -> None:
    features = np.array([[0.0], [1.0]])
    target = np.array([0.0, 1.0])
    estimator = resolve_estimator(_ridge_spec())
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        estimator.fit(features, target, (FoldRole.TRAIN, FoldRole.PURGED))
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        estimator.fit(features, target, {"fold_role": [FoldRole.TRAIN, FoldRole.EMBARGOED]})


def test_fit_accepts_train_only_metadata() -> None:
    features = np.array([[0.0], [1.0], [2.0]])
    target = np.array([0.0, 1.0, 2.0])
    fitted = resolve_estimator(_ridge_spec()).fit(
        features, target, (FoldRole.TRAIN, FoldRole.TRAIN, FoldRole.TRAIN)
    )
    assert fitted.predict(features).shape == (3,)


def test_logistic_rejects_ternary_labels() -> None:
    features = np.array([[0.0], [1.0], [2.0], [3.0], [4.0], [5.0]])
    target = np.array([0, 1, 2, 0, 1, 2])
    with pytest.raises(PredictiveSpecError, match="binary classification only"):
        resolve_estimator(_logistic_spec()).fit(features, target, None)


def test_logistic_rejects_multinomial_hyperparameter() -> None:
    with pytest.raises(PredictiveSpecError, match="binary classification only"):
        resolve_estimator(_logistic_spec(multi_class="multinomial"))


def test_ridge_rejects_classification_task_type() -> None:
    spec = EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={},
        seed=1,
        task_type=TaskType.CLASSIFICATION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type REGRESSION"):
        resolve_estimator(spec)


def test_logistic_rejects_regression_task_type() -> None:
    spec = EstimatorSpec(
        family="sklearn.logistic",
        hyperparameters={},
        seed=1,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type CLASSIFICATION"):
        resolve_estimator(spec)


def test_unknown_hyperparameter_is_spec_error() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown hyperparameters"):
        resolve_estimator(_ridge_spec(not_a_param=1.0)).fit(
            np.array([[0.0], [1.0]]), np.array([0.0, 1.0]), None
        )


def test_ridge_recovers_linear_signal() -> None:
    rng = np.random.default_rng(0)
    features = rng.normal(size=(200, 3))
    target = 2.5 * features[:, 0] - 1.25 * features[:, 1] + 0.02 * rng.normal(size=200)
    predicted = (
        resolve_estimator(_ridge_spec(alpha=0.1)).fit(features, target, None).predict(features)
    )
    correlation = float(np.corrcoef(target, predicted)[0, 1])
    assert correlation > 0.95


def test_custom_preprocessing_spec_is_honored() -> None:
    features = np.array([[1.0, np.nan], [3.0, 5.0], [5.0, 7.0]])
    target = np.array([1.0, 2.0, 3.0])
    estimator = SklearnPredictiveEstimator(
        _ridge_spec(),
        preprocessing=PreprocessingSpec(steps=(PreprocessingStep.IMPUTE_MEDIAN,)),
    )
    stats = estimator.fit(features, target, None).preprocessing_statistics()
    assert "impute_median" in stats
    assert "standardize_mean" not in stats
