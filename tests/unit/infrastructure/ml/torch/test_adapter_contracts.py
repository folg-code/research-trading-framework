"""Torch adapter contract tests that must pass without extra dl."""

from __future__ import annotations

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.infrastructure.ml.torch.adapter import TorchFeedforwardAdapter
from trading_framework.research.predictive import (
    EstimatorSpec,
    FoldRole,
    PredictiveExtraError,
    PredictiveSpecError,
    SequenceWindowSpec,
    TaskType,
)


def _regressor_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="torch.feedforward.regressor",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def _classifier_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="torch.feedforward.classifier",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.CLASSIFICATION,
    )


def test_gpu_device_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="GPU/CUDA/MPS"):
        resolve_estimator(_regressor_spec(device="cuda"))


def test_mps_device_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="GPU/CUDA/MPS"):
        resolve_estimator(_regressor_spec(device="mps"))


def test_cuda_index_device_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="GPU/CUDA/MPS"):
        resolve_estimator(_classifier_spec(device="cuda:0"))


def test_unknown_hyperparameter_is_spec_error() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown hyperparameters"):
        resolve_estimator(_regressor_spec(not_a_param=1.0))


def test_non_relu_activation_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="activation"):
        resolve_estimator(_regressor_spec(activation="tanh"))


def test_non_adam_optimizer_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="optimizer"):
        resolve_estimator(_regressor_spec(optimizer="sgd"))


def test_task_type_mismatch_is_rejected() -> None:
    spec = EstimatorSpec(
        family="torch.feedforward.regressor",
        hyperparameters={},
        seed=0,
        task_type=TaskType.CLASSIFICATION,
    )
    with pytest.raises(PredictiveSpecError, match="requires task_type"):
        resolve_estimator(spec)


def test_sequence_family_stays_unregistered() -> None:
    spec = EstimatorSpec(
        family="torch.lstm.regressor",
        hyperparameters={},
        seed=0,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="unknown estimator family") as caught:
        resolve_estimator(spec)
    assert not isinstance(caught.value, PredictiveExtraError)


def test_outer_test_early_stopping_hyperparameter_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="early stopping"):
        resolve_estimator(_regressor_spec(early_stopping_eval_role="TEST"))


def test_outer_test_early_stopping_metadata_is_rejected() -> None:
    estimator = TorchFeedforwardAdapter(_regressor_spec(max_epochs=5, hidden_sizes=(16,)))
    features = np.zeros((4, 2), dtype=np.float64)
    target = np.zeros(4, dtype=np.float64)
    with pytest.raises(PredictiveSpecError, match="early stopping"):
        estimator.fit(features, target, {"early_stopping_eval_role": FoldRole.TEST})


def test_sequence_window_spec_is_rejected() -> None:
    estimator = TorchFeedforwardAdapter(_regressor_spec(max_epochs=5, hidden_sizes=(16,)))
    features = np.zeros((4, 2), dtype=np.float64)
    target = np.zeros(4, dtype=np.float64)
    with pytest.raises(PredictiveSpecError, match="SequenceWindowSpec"):
        estimator.fit(features, target, SequenceWindowSpec(lookback_bars=4))


def test_max_epochs_cap_is_enforced() -> None:
    with pytest.raises(PredictiveSpecError, match="max_epochs"):
        resolve_estimator(_regressor_spec(max_epochs=201))
