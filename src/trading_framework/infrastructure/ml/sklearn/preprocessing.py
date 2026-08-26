"""Sklearn implementation of domain PreprocessingSpec (D-S040-14).

Fits on the feature matrix passed to ``fit()`` only. Callers must pass TRAIN
rows; this module does not filter fold roles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, assert_never

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


@dataclass(frozen=True, slots=True)
class FittedSklearnPreprocessor:
    """Fold-local sklearn transforms fitted on one TRAIN feature matrix."""

    spec: PreprocessingSpec
    _pipeline: Any

    def transform(self, features: object) -> np.ndarray:
        transformed = self._pipeline.transform(as_feature_matrix(features))
        return np.asarray(transformed, dtype=np.float64)

    def pipeline(self) -> Any:
        """Return the fitted sklearn Pipeline for opaque artifact persistence."""
        return self._pipeline

    def statistics(self) -> dict[str, list[float]]:
        """JSON-stable per-column statistics from the fitted sklearn steps."""
        payload: dict[str, list[float]] = {}
        named_steps: dict[str, Any] = dict(self._pipeline.named_steps)
        imputer = named_steps.get(PreprocessingStep.IMPUTE_MEDIAN.value)
        if imputer is not None and getattr(imputer, "statistics_", None) is not None:
            payload["impute_median"] = [
                float(value) for value in np.asarray(imputer.statistics_).ravel()
            ]
        scaler = named_steps.get(PreprocessingStep.STANDARDIZE.value)
        if scaler is not None:
            if getattr(scaler, "mean_", None) is not None:
                payload["standardize_mean"] = [
                    float(value) for value in np.asarray(scaler.mean_).ravel()
                ]
            if getattr(scaler, "scale_", None) is not None:
                payload["standardize_scale"] = [
                    float(value) for value in np.asarray(scaler.scale_).ravel()
                ]
        return payload


def fit_sklearn_preprocessor(
    spec: PreprocessingSpec,
    features: object,
) -> FittedSklearnPreprocessor:
    """Fit ``spec`` on ``features`` only. Do not reuse across folds."""
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    matrix = as_feature_matrix(features)
    steps: list[tuple[str, Any]] = []
    for step in spec.steps:
        if step is PreprocessingStep.IMPUTE_MEDIAN:
            steps.append((step.value, SimpleImputer(strategy="median")))
        elif step is PreprocessingStep.STANDARDIZE:
            steps.append((step.value, StandardScaler()))
        else:
            assert_never(step)
    pipeline = Pipeline(steps)
    pipeline.fit(matrix)
    return FittedSklearnPreprocessor(spec=spec, _pipeline=pipeline)
