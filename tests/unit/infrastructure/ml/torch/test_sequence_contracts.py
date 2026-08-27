"""Sequence-family contract tests that must pass without extra dl."""

from __future__ import annotations

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.infrastructure.ml.torch.sequence import TorchSequenceAdapter
from trading_framework.research.predictive import (
    EstimatorSpec,
    PredictiveSpecError,
    SequenceWindowSpec,
    TaskType,
)


def _lstm_spec(**hyperparameters: object) -> EstimatorSpec:
    return EstimatorSpec(
        family="torch.lstm.regressor",
        hyperparameters=hyperparameters,
        seed=7,
        task_type=TaskType.REGRESSION,
    )


def test_bidirectional_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="bidirectional"):
        resolve_estimator(_lstm_spec(bidirectional=True))


def test_num_layers_above_two_is_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="num_layers"):
        resolve_estimator(_lstm_spec(num_layers=3))


def test_hidden_size_cap_is_enforced() -> None:
    with pytest.raises(PredictiveSpecError, match="hidden_size"):
        resolve_estimator(_lstm_spec(hidden_size=129))


def test_feedforward_keys_are_unknown_on_sequence_family() -> None:
    with pytest.raises(PredictiveSpecError, match="unknown hyperparameters"):
        resolve_estimator(_lstm_spec(hidden_sizes=[16]))


def test_sequence_family_requires_window_spec() -> None:
    estimator = TorchSequenceAdapter(_lstm_spec(max_epochs=5, hidden_size=8))
    windows = np.zeros((12, 4, 2), dtype=np.float64)
    target = np.zeros(12, dtype=np.float64)
    with pytest.raises(PredictiveSpecError, match="SequenceWindowSpec"):
        estimator.fit(windows, target, {"scaler_features": np.zeros((20, 2))})


def test_sequence_family_rejects_rank_two_features() -> None:
    estimator = TorchSequenceAdapter(_lstm_spec(max_epochs=5, hidden_size=8))
    features = np.zeros((12, 2), dtype=np.float64)
    target = np.zeros(12, dtype=np.float64)
    metadata = {
        "window_spec": SequenceWindowSpec(lookback_bars=4),
        "scaler_features": np.zeros((20, 2)),
    }
    with pytest.raises(PredictiveSpecError, match="3-dimensional"):
        estimator.fit(features, target, metadata)


def test_sequence_family_requires_scaler_feature_rows() -> None:
    estimator = TorchSequenceAdapter(_lstm_spec(max_epochs=5, hidden_size=8))
    windows = np.zeros((12, 4, 2), dtype=np.float64)
    target = np.zeros(12, dtype=np.float64)
    with pytest.raises(PredictiveSpecError, match="2d TRAIN feature rows"):
        estimator.fit(windows, target, {"window_spec": SequenceWindowSpec(lookback_bars=4)})
