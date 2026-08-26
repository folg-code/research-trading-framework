"""Smoke tests that require the optional ml extra (scikit-learn)."""

from __future__ import annotations

import pytest

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml


def test_sklearn_extra_is_importable() -> None:
    import sklearn

    assert sklearn.__version__


def test_registry_resolves_sklearn_ridge_when_extra_installed() -> None:
    from trading_framework.infrastructure.ml.registry import resolve_estimator
    from trading_framework.research.predictive import EstimatorSpec, TaskType

    estimator = resolve_estimator(
        EstimatorSpec(
            family="sklearn.ridge",
            hyperparameters={"alpha": 1.0},
            seed=0,
            task_type=TaskType.REGRESSION,
        )
    )
    assert estimator is not None


def test_unknown_family_is_still_validation_error_when_extra_installed() -> None:
    from trading_framework.infrastructure.ml.registry import resolve_estimator
    from trading_framework.research.predictive import (
        EstimatorSpec,
        PredictiveExtraError,
        PredictiveSpecError,
        TaskType,
    )

    spec = EstimatorSpec(
        family="not.a.family",
        hyperparameters={},
        seed=1,
        task_type=TaskType.CLASSIFICATION,
    )
    with pytest.raises(PredictiveSpecError, match="unknown estimator family") as caught:
        resolve_estimator(spec)
    assert not isinstance(caught.value, PredictiveExtraError)
