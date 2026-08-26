"""Smoke tests that require the optional ml-trees extra."""

from __future__ import annotations

import pytest

pytest.importorskip("xgboost")

pytestmark = pytest.mark.ml_trees


def test_xgboost_extra_is_importable() -> None:
    import xgboost

    assert xgboost.__version__


def test_registry_resolves_xgboost_regressor_when_extra_installed() -> None:
    pytest.importorskip("sklearn")
    from trading_framework.infrastructure.ml.registry import resolve_estimator
    from trading_framework.research.predictive import EstimatorSpec, TaskType

    estimator = resolve_estimator(
        EstimatorSpec(
            family="xgboost.regressor",
            hyperparameters={"n_estimators": 10},
            seed=0,
            task_type=TaskType.REGRESSION,
        )
    )
    assert estimator is not None
