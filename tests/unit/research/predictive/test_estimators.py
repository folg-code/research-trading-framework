"""Unit tests for EstimatorSpec, TaskType, and the structural protocol."""

from __future__ import annotations

from types import MappingProxyType
from typing import get_type_hints

import numpy as np
import pytest

from trading_framework.research.predictive import (
    EstimatorSpec,
    FittedPredictiveEstimator,
    PredictiveEstimator,
    PredictiveSpecError,
    TaskType,
)
from trading_framework.research.predictive.estimators import EstimatorDescription


def test_task_type_values() -> None:
    assert TaskType.REGRESSION == "REGRESSION"
    assert TaskType.CLASSIFICATION == "CLASSIFICATION"


def test_estimator_spec_requires_seed() -> None:
    with pytest.raises(TypeError):
        EstimatorSpec(  # type: ignore[call-arg]
            family="sklearn.ridge",
            hyperparameters={},
            task_type=TaskType.REGRESSION,
        )


def test_estimator_spec_rejects_non_integer_seed() -> None:
    with pytest.raises(PredictiveSpecError, match="seed must be an integer"):
        EstimatorSpec.from_dict(
            {
                "family": "sklearn.ridge",
                "hyperparameters": {},
                "seed": True,
                "task_type": "REGRESSION",
            }
        )
    with pytest.raises(PredictiveSpecError, match="seed must be an integer"):
        EstimatorSpec.from_dict(
            {
                "family": "sklearn.ridge",
                "hyperparameters": {},
                "seed": 1.5,
                "task_type": "REGRESSION",
            }
        )


def test_estimator_spec_rejects_empty_family() -> None:
    with pytest.raises(PredictiveSpecError, match="family must be non-empty"):
        EstimatorSpec(
            family="  ",
            hyperparameters={},
            seed=7,
            task_type=TaskType.REGRESSION,
        )


def test_estimator_spec_strips_family() -> None:
    spec = EstimatorSpec(
        family=" sklearn.ridge ",
        hyperparameters={"alpha": 1.0},
        seed=0,
        task_type=TaskType.REGRESSION,
    )
    assert spec.family == "sklearn.ridge"


def test_estimator_spec_canonicalizes_hyperparameters() -> None:
    spec = EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"l1_ratio": 0.5, "alpha": 1.0},
        seed=3,
        task_type=TaskType.REGRESSION,
    )
    assert list(spec.hyperparameters) == ["alpha", "l1_ratio"]
    assert spec.hyperparameters["alpha"] == 1.0
    assert isinstance(spec.hyperparameters, MappingProxyType)


def test_estimator_spec_rejects_non_json_hyperparameters() -> None:
    with pytest.raises(PredictiveSpecError, match="JSON-serializable"):
        EstimatorSpec(
            family="sklearn.ridge",
            hyperparameters={"alpha": object()},
            seed=1,
            task_type=TaskType.REGRESSION,
        )


def test_estimator_spec_rejects_nan_hyperparameters() -> None:
    with pytest.raises(PredictiveSpecError, match="JSON-serializable"):
        EstimatorSpec(
            family="sklearn.ridge",
            hyperparameters={"alpha": float("nan")},
            seed=1,
            task_type=TaskType.REGRESSION,
        )


def test_estimator_spec_round_trip() -> None:
    spec = EstimatorSpec(
        family="sklearn.logistic",
        hyperparameters={"C": 1.0},
        seed=11,
        task_type=TaskType.CLASSIFICATION,
    )
    restored = EstimatorSpec.from_dict(spec.to_dict())
    assert restored == spec


def test_estimator_spec_from_dict_rejects_invalid_task_type() -> None:
    with pytest.raises(PredictiveSpecError, match="invalid estimator task_type"):
        EstimatorSpec.from_dict(
            {
                "family": "sklearn.ridge",
                "hyperparameters": {},
                "seed": 1,
                "task_type": "CLUSTERING",
            }
        )


def test_protocols_are_structural() -> None:
    assert getattr(PredictiveEstimator, "_is_protocol", False)
    assert getattr(FittedPredictiveEstimator, "_is_protocol", False)
    hints = get_type_hints(PredictiveEstimator.fit)
    assert hints["features"] is np.ndarray
    assert hints["return"] is FittedPredictiveEstimator


def test_estimator_description_freezes_resolved_params() -> None:
    description = EstimatorDescription(
        library="sklearn",
        version="1.6.0",
        resolved_params={"alpha": 1.0},
    )
    assert isinstance(description.resolved_params, MappingProxyType)
    assert description.resolved_params["alpha"] == 1.0
