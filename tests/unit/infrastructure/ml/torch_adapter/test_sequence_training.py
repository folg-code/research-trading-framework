"""Gated LSTM/GRU training tests (D-S043-11 / D-S043-12 / D-S043-14 / D-S043-15)."""

from __future__ import annotations

import os

import numpy as np
import pytest

from trading_framework.infrastructure.ml.registry import resolve_estimator
from trading_framework.infrastructure.ml.torch.adapter import FittedTorchEstimator
from trading_framework.research.predictive import EstimatorSpec, SequenceWindowSpec, TaskType
from trading_framework.research.predictive.preprocessing import default_preprocessing_spec
from trading_framework.research.predictive.promotion.preprocessing import fit_numpy_preprocessor

pytest.importorskip("torch")

pytestmark = [
    pytest.mark.torch,
    pytest.mark.skipif(
        os.getenv("TRADING_FRAMEWORK_RUN_TORCH_TESTS") != "1",
        reason="set TRADING_FRAMEWORK_RUN_TORCH_TESTS=1 to run torch training tests",
    ),
]


def _sequence_spec(family: str, *, task_type: TaskType, **hyperparameters: object) -> EstimatorSpec:
    defaults: dict[str, object] = {
        "max_epochs": 5,
        "batch_size": 16,
        "hidden_size": 8,
        "num_layers": 1,
        "patience": 5,
    }
    defaults.update(hyperparameters)
    return EstimatorSpec(
        family=family,
        hyperparameters=defaults,
        seed=11,
        task_type=task_type,
    )


def _window_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    rng = np.random.default_rng(0)
    rows = rng.normal(size=(70, 3)).astype(np.float64)
    windows = np.stack([rows[index : index + 4] for index in range(64)])
    target = (0.8 * windows[:, -1, 0] - 0.3 * windows[:, -1, 1]).astype(np.float64)
    metadata: dict[str, object] = {
        "window_spec": SequenceWindowSpec(lookback_bars=4),
        "scaler_features": rows,
    }
    return rows, windows, target, metadata


def test_lstm_regressor_fit_predict() -> None:
    _rows, windows, target, metadata = _window_fixture()
    fitted = resolve_estimator(
        _sequence_spec("torch.lstm.regressor", task_type=TaskType.REGRESSION)
    ).fit(windows, target, metadata)
    predicted = fitted.predict(windows)
    assert predicted.shape == (64,)
    assert fitted.predict_proba(windows) is None
    assert fitted.native_feature_importance() is None
    params = dict(fitted.describe().resolved_params)
    assert params["cell"] == "lstm"
    assert params["hidden_size"] == 8
    assert params["num_layers"] == 1
    assert params["reproducibility_atol"] == 1e-5
    assert params["reproducibility_rtol"] == 1e-4


def test_gru_classifier_fit_predict_proba() -> None:
    _rows, windows, _target, metadata = _window_fixture()
    labels = (windows[:, -1, 0] > 0.0).astype(np.int64)
    fitted = resolve_estimator(
        _sequence_spec("torch.gru.classifier", task_type=TaskType.CLASSIFICATION)
    ).fit(windows, labels, metadata)
    predicted = fitted.predict(windows)
    proba = fitted.predict_proba(windows)
    assert predicted.shape == (64,)
    assert proba is not None
    assert proba.shape == (64, 2)


def test_lstm_repeated_fit_is_allclose() -> None:
    _rows, windows, target, metadata = _window_fixture()
    spec = _sequence_spec("torch.lstm.regressor", task_type=TaskType.REGRESSION)
    first = resolve_estimator(spec).fit(windows, target, metadata).predict(windows)
    second = resolve_estimator(spec).fit(windows, target, metadata).predict(windows)
    np.testing.assert_allclose(first, second, atol=1e-5, rtol=1e-4)


def test_scaler_is_fitted_on_2d_train_rows_not_windows() -> None:
    rows, windows, target, metadata = _window_fixture()
    fitted = resolve_estimator(
        _sequence_spec("torch.lstm.regressor", task_type=TaskType.REGRESSION)
    ).fit(windows, target, metadata)
    assert isinstance(fitted, FittedTorchEstimator)
    expected = fit_numpy_preprocessor(default_preprocessing_spec(), rows).statistics()
    flattened = windows.reshape(-1, windows.shape[2])
    windowed = fit_numpy_preprocessor(default_preprocessing_spec(), flattened).statistics()
    assert fitted.preprocessing_statistics() == expected
    assert fitted.preprocessing_statistics() != windowed


def test_scaler_statistics_differ_across_fold_rows() -> None:
    rows, windows, target, metadata = _window_fixture()
    first = resolve_estimator(
        _sequence_spec("torch.lstm.regressor", task_type=TaskType.REGRESSION)
    ).fit(windows, target, metadata)
    shifted_meta = {
        "window_spec": SequenceWindowSpec(lookback_bars=4),
        "scaler_features": rows + 10.0,
    }
    second = resolve_estimator(
        _sequence_spec("torch.lstm.regressor", task_type=TaskType.REGRESSION)
    ).fit(windows, target, shifted_meta)
    assert isinstance(first, FittedTorchEstimator)
    assert isinstance(second, FittedTorchEstimator)
    assert first.preprocessing_statistics() != second.preprocessing_statistics()
