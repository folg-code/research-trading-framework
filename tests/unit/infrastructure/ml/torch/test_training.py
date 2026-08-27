"""Gated torch training-loop tests (D-S043-07 / D-S043-13 / D-S043-14)."""

from __future__ import annotations

import json
import os

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import dump_fitted_estimator, resolve_estimator
from trading_framework.infrastructure.ml.torch.adapter import FittedTorchEstimator
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PredictiveSpecError,
    TaskType,
)

pytest.importorskip("torch")

pytestmark = [
    pytest.mark.torch,
    pytest.mark.skipif(
        os.getenv("TRADING_FRAMEWORK_RUN_TORCH_TESTS") != "1",
        reason="set TRADING_FRAMEWORK_RUN_TORCH_TESTS=1 to run torch training tests",
    ),
]


def _regressor_spec(**hyperparameters: object) -> EstimatorSpec:
    defaults: dict[str, object] = {
        "max_epochs": 5,
        "batch_size": 16,
        "hidden_sizes": [16],
        "patience": 5,
    }
    defaults.update(hyperparameters)
    return EstimatorSpec(
        family="torch.feedforward.regressor",
        hyperparameters=defaults,
        seed=11,
        task_type=TaskType.REGRESSION,
    )


def _classifier_spec(**hyperparameters: object) -> EstimatorSpec:
    defaults: dict[str, object] = {
        "max_epochs": 5,
        "batch_size": 16,
        "hidden_sizes": [16],
        "patience": 5,
    }
    defaults.update(hyperparameters)
    return EstimatorSpec(
        family="torch.feedforward.classifier",
        hyperparameters=defaults,
        seed=11,
        task_type=TaskType.CLASSIFICATION,
    )


def _regression_fixture() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    features = rng.normal(size=(64, 3)).astype(np.float64)
    target = (0.8 * features[:, 0] - 0.3 * features[:, 1]).astype(np.float64)
    return features, target


def _classification_fixture() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(1)
    features = rng.normal(size=(64, 3)).astype(np.float64)
    target = (features[:, 0] > 0.0).astype(np.int64)
    return features, target


def test_regressor_fit_predict_returns_none_proba() -> None:
    features, target = _regression_fixture()
    fitted = resolve_estimator(_regressor_spec()).fit(features, target, None)
    predicted = fitted.predict(features)
    assert predicted.shape == (64,)
    assert fitted.predict_proba(features) is None
    assert fitted.native_feature_importance() is None


def test_classifier_fit_predict_and_predict_proba() -> None:
    features, target = _classification_fixture()
    fitted = resolve_estimator(_classifier_spec()).fit(features, target, None)
    predicted = fitted.predict(features)
    proba = fitted.predict_proba(features)
    assert predicted.shape == (64,)
    assert proba is not None
    assert proba.shape == (64, 2)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, rtol=1e-5, atol=1e-5)


def test_describe_records_stopping_epoch_and_cpu_threads() -> None:
    import torch

    features, target = _regression_fixture()
    description = resolve_estimator(_regressor_spec()).fit(features, target, None).describe()
    assert description.library == "torch"
    assert description.version == torch.__version__
    params = dict(description.resolved_params)
    assert params["device"] == "cpu"
    assert params["num_threads"] == 1
    assert params["optimizer"] == "adam"
    assert params["loss"] == "mse"
    assert params["reproducibility_atol"] == 1e-5
    assert params["reproducibility_rtol"] == 1e-4
    assert params["stopping_epoch"] >= 1
    assert params["stopping_epoch"] <= 5
    assert len(params["inner_validation_loss"]) == len(params["inner_train_loss"])
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert json.loads(canonical) == params


def test_repeated_fit_is_allclose_on_one_process() -> None:
    features, target = _regression_fixture()
    spec = _regressor_spec()
    first = resolve_estimator(spec).fit(features, target, None).predict(features)
    second = resolve_estimator(spec).fit(features, target, None).predict(features)
    np.testing.assert_allclose(first, second, atol=1e-5, rtol=1e-4)


def test_fit_rejects_purged_metadata() -> None:
    features, target = _regression_fixture()
    roles = tuple([FoldRole.TRAIN] * 63 + [FoldRole.PURGED])
    estimator = resolve_estimator(_regressor_spec())
    with pytest.raises(PredictiveSpecError, match="TRAIN rows only"):
        estimator.fit(features, target, roles)


def test_serialize_artifact_is_opaque_bytes() -> None:
    features, target = _regression_fixture()
    fitted = resolve_estimator(_regressor_spec()).fit(features, target, None)
    payload = dump_fitted_estimator(fitted)
    assert isinstance(payload, bytes)
    assert len(payload) > 0


def test_preprocessor_statistics_are_fold_local() -> None:
    features, target = _regression_fixture()
    first = resolve_estimator(_regressor_spec()).fit(features, target, None)
    shifted = features + 10.0
    second = resolve_estimator(_regressor_spec()).fit(shifted, target, None)
    assert isinstance(first, FittedTorchEstimator)
    assert isinstance(second, FittedTorchEstimator)
    assert first.preprocessing_statistics() != second.preprocessing_statistics()
