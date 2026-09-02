"""Numpy implementation of domain PreprocessingSpec for neural families (D-S043-15).

Moved here from ``infrastructure/ml/torch/preprocessing.py`` (Sprint 049 Q8 /
D-S049-08): this is the promoted-artifact evaluator's preprocessing half, and
the domain layer (``research/predictive/``) is where Sprint 050's Market
Analysis component must be able to reach it from, without pulling in torch.

Fits on the 2d feature matrix passed to ``fit()`` only. Does not import
sklearn or torch, so extra ``dl`` does not require extra ``ml``. The torch
adapter (``infrastructure/ml/torch/``) imports this module downward.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

import numpy as np

from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.preprocessing import (
    PreprocessingSpec,
    PreprocessingStep,
)


def as_feature_matrix(features: object) -> np.ndarray:
    """Coerce ``features`` to a non-empty float64 matrix of shape ``(n, p)``."""
    array = np.asarray(features, dtype=np.float64)
    if array.ndim != 2:
        msg = f"feature matrix must be 2-dimensional, got {array.ndim} dimensions"
        raise PredictiveSpecError(msg)
    if array.shape[0] == 0 or array.shape[1] == 0:
        msg = "feature matrix must be non-empty"
        raise PredictiveSpecError(msg)
    return array


def as_sequence_windows(features: object, *, lookback_bars: int) -> np.ndarray:
    """Coerce ``features`` to rank-3 float64 windows ``(n, lookback, p)``."""
    array = np.asarray(features, dtype=np.float64)
    if array.ndim != 3:
        msg = f"sequence windows must be 3-dimensional, got {array.ndim} dimensions"
        raise PredictiveSpecError(msg)
    if array.shape[0] == 0 or array.shape[2] == 0:
        msg = "sequence windows must be non-empty"
        raise PredictiveSpecError(msg)
    if array.shape[1] != lookback_bars:
        msg = (
            f"sequence windows lookback is {array.shape[1]}; "
            f"SequenceWindowSpec.lookback_bars is {lookback_bars}"
        )
        raise PredictiveSpecError(msg)
    return array


def transform_windows(
    preprocessor: FittedNumpyPreprocessor,
    windows: np.ndarray,
) -> np.ndarray:
    """Apply a 2d-fitted preprocessor to every timestep of every window."""
    n_windows, lookback, n_features = windows.shape
    flat = windows.reshape(n_windows * lookback, n_features)
    transformed = preprocessor.transform(flat)
    return transformed.reshape(n_windows, lookback, n_features)


@dataclass(frozen=True, slots=True)
class FittedNumpyPreprocessor:
    """Fold-local numpy transforms fitted on one TRAIN feature matrix."""

    spec: PreprocessingSpec
    impute_median: tuple[float, ...] | None = None
    standardize_mean: tuple[float, ...] | None = None
    standardize_scale: tuple[float, ...] | None = None

    def transform(self, features: object) -> np.ndarray:
        matrix = as_feature_matrix(features)
        n_features = _expected_n_features(self)
        if matrix.shape[1] != n_features:
            msg = (
                f"feature matrix has {matrix.shape[1]} columns; "
                f"preprocessor was fitted on {n_features}"
            )
            raise PredictiveSpecError(msg)
        transformed = matrix
        if self.impute_median is not None:
            transformed = _impute_median(transformed, self.impute_median)
        if self.standardize_mean is not None and self.standardize_scale is not None:
            mean = np.asarray(self.standardize_mean, dtype=np.float64)
            scale = np.asarray(self.standardize_scale, dtype=np.float64)
            transformed = (transformed - mean) / scale
        return np.asarray(transformed, dtype=np.float64)

    def statistics(self) -> dict[str, list[float]]:
        """JSON-stable per-column statistics from the fitted numpy steps."""
        payload: dict[str, list[float]] = {}
        if self.impute_median is not None:
            payload["impute_median"] = [float(value) for value in self.impute_median]
        if self.standardize_mean is not None:
            payload["standardize_mean"] = [float(value) for value in self.standardize_mean]
        if self.standardize_scale is not None:
            payload["standardize_scale"] = [float(value) for value in self.standardize_scale]
        return payload


def fit_numpy_preprocessor(
    spec: PreprocessingSpec,
    features: object,
) -> FittedNumpyPreprocessor:
    """Fit ``spec`` on ``features`` only. Do not reuse across folds."""
    matrix = as_feature_matrix(features)
    impute_median: tuple[float, ...] | None = None
    standardize_mean: tuple[float, ...] | None = None
    standardize_scale: tuple[float, ...] | None = None
    working = matrix
    for step in spec.steps:
        if step is PreprocessingStep.IMPUTE_MEDIAN:
            impute_median = tuple(float(value) for value in np.nanmedian(working, axis=0))
            working = _impute_median(working, impute_median)
        elif step is PreprocessingStep.STANDARDIZE:
            mean = np.nanmean(working, axis=0)
            scale = np.nanstd(working, axis=0, ddof=0)
            scale = np.where(scale == 0.0, 1.0, scale)
            standardize_mean = tuple(float(value) for value in mean)
            standardize_scale = tuple(float(value) for value in scale)
            working = (working - mean) / scale
        else:
            assert_never(step)
    return FittedNumpyPreprocessor(
        spec=spec,
        impute_median=impute_median,
        standardize_mean=standardize_mean,
        standardize_scale=standardize_scale,
    )


def _impute_median(matrix: np.ndarray, medians: tuple[float, ...]) -> np.ndarray:
    filled = np.array(matrix, dtype=np.float64, copy=True)
    values = np.asarray(medians, dtype=np.float64)
    missing = np.isnan(filled)
    if missing.any():
        filled[missing] = np.take(values, np.where(missing)[1])
    return filled


def _expected_n_features(preprocessor: FittedNumpyPreprocessor) -> int:
    for stats in (
        preprocessor.impute_median,
        preprocessor.standardize_mean,
        preprocessor.standardize_scale,
    ):
        if stats is not None:
            return len(stats)
    msg = "fitted preprocessor has no column statistics"
    raise PredictiveSpecError(msg)
