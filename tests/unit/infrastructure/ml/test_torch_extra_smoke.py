"""Smoke tests that require the optional dl extra (CPU PyTorch)."""

from __future__ import annotations

import pytest

pytest.importorskip("torch")

pytestmark = pytest.mark.torch


def test_torch_extra_is_importable() -> None:
    import torch

    assert torch.__version__


def test_registry_resolves_feedforward_regressor_when_extra_installed() -> None:
    from trading_framework.infrastructure.ml.registry import resolve_estimator
    from trading_framework.research.predictive import EstimatorSpec, TaskType

    estimator = resolve_estimator(
        EstimatorSpec(
            family="torch.feedforward.regressor",
            hyperparameters={"max_epochs": 5, "hidden_sizes": [16]},
            seed=0,
            task_type=TaskType.REGRESSION,
        )
    )
    assert estimator is not None


def test_registry_resolves_lstm_regressor_when_extra_installed() -> None:
    from trading_framework.infrastructure.ml.registry import resolve_estimator
    from trading_framework.research.predictive import EstimatorSpec, TaskType

    estimator = resolve_estimator(
        EstimatorSpec(
            family="torch.lstm.regressor",
            hyperparameters={"max_epochs": 5, "hidden_size": 8},
            seed=0,
            task_type=TaskType.REGRESSION,
        )
    )
    assert estimator is not None
