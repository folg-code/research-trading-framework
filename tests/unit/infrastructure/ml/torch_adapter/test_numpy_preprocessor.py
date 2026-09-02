"""Numpy preprocessor tests that must pass without extra dl."""

from __future__ import annotations

import numpy as np
import pytest

from trading_framework.infrastructure.ml.torch.preprocessing import (
    as_feature_matrix,
    fit_numpy_preprocessor,
    transform_windows,
)
from trading_framework.research.predictive import PredictiveSpecError
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    PreprocessingStep,
)


def test_as_feature_matrix_rejects_rank_three() -> None:
    with pytest.raises(PredictiveSpecError, match="2-dimensional"):
        as_feature_matrix(np.zeros((4, 3, 2)))


def test_impute_median_then_standardize() -> None:
    matrix = np.array(
        [
            [1.0, np.nan],
            [3.0, 2.0],
            [5.0, 4.0],
        ],
        dtype=np.float64,
    )
    fitted = fit_numpy_preprocessor(PreprocessingSpec(), matrix)
    transformed = fitted.transform(matrix)
    assert transformed.shape == (3, 2)
    assert not np.isnan(transformed).any()
    stats = fitted.statistics()
    assert stats["impute_median"][0] == pytest.approx(3.0)
    assert stats["impute_median"][1] == pytest.approx(3.0)
    np.testing.assert_allclose(transformed.mean(axis=0), 0.0, atol=1e-12)


def test_zero_variance_scale_is_one() -> None:
    matrix = np.array([[2.0, 1.0], [2.0, 3.0], [2.0, 5.0]], dtype=np.float64)
    fitted = fit_numpy_preprocessor(
        PreprocessingSpec(steps=(PreprocessingStep.STANDARDIZE,)),
        matrix,
    )
    assert fitted.standardize_scale is not None
    assert fitted.standardize_scale[0] == pytest.approx(1.0)
    transformed = fitted.transform(matrix)
    np.testing.assert_allclose(transformed[:, 0], 0.0)


def test_transform_windows_applies_2d_statistics_per_timestep() -> None:
    rows = np.array([[0.0, 2.0], [2.0, 4.0], [4.0, 6.0]], dtype=np.float64)
    fitted = fit_numpy_preprocessor(
        PreprocessingSpec(steps=(PreprocessingStep.STANDARDIZE,)),
        rows,
    )
    windows = np.stack([rows[:2], rows[1:]], axis=0)
    transformed = transform_windows(fitted, windows)
    assert transformed.shape == (2, 2, 2)
    expected = fitted.transform(rows)
    np.testing.assert_allclose(transformed[0], expected[:2])
    np.testing.assert_allclose(transformed[1], expected[1:])


def test_preprocessor_statistics_differ_for_different_train_matrices() -> None:
    first = fit_numpy_preprocessor(
        PreprocessingSpec(),
        np.array([[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]], dtype=np.float64),
    )
    second = fit_numpy_preprocessor(
        PreprocessingSpec(),
        np.array([[10.0, 20.0], [30.0, 40.0], [50.0, 60.0]], dtype=np.float64),
    )
    assert first.statistics() != second.statistics()
