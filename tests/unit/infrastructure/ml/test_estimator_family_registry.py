"""Registry tests that must pass without the ml extra installed."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from trading_framework.infrastructure.ml.registry import (
    registered_families,
    resolve_estimator,
)
from trading_framework.infrastructure.ml.sklearn import factories as sklearn_factories
from trading_framework.research.predictive import (
    EstimatorSpec,
    PredictiveExtraError,
    PredictiveSpecError,
    TaskType,
)


def _ridge_spec() -> EstimatorSpec:
    return EstimatorSpec(
        family="sklearn.ridge",
        hyperparameters={"alpha": 1.0},
        seed=0,
        task_type=TaskType.REGRESSION,
    )


def _module_level_imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _is_sklearn(module_name: str) -> bool:
    return module_name == "sklearn" or module_name.startswith("sklearn.")


def test_registered_sklearn_families() -> None:
    families = registered_families()
    assert families["sklearn.ridge"] == "ml"
    assert families["sklearn.elastic_net"] == "ml"
    assert families["sklearn.logistic"] == "ml"
    assert families["xgboost.regressor"] == "ml-trees"
    assert families["xgboost.classifier"] == "ml-trees"


def test_unknown_family_is_validation_error() -> None:
    spec = EstimatorSpec(
        family="sklearn.unknown",
        hyperparameters={},
        seed=1,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveSpecError, match="unknown estimator family") as caught:
        resolve_estimator(spec)
    assert not isinstance(caught.value, PredictiveExtraError)


def test_missing_extra_raises_predictive_extra_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_sklearn() -> object:
        raise ImportError("sklearn is not installed")

    monkeypatch.setattr(sklearn_factories, "_import_sklearn", missing_sklearn)
    with pytest.raises(PredictiveExtraError) as caught:
        resolve_estimator(_ridge_spec())
    message = str(caught.value)
    assert "ml" in message
    assert "sklearn.ridge" in message
    assert isinstance(caught.value.__cause__, ImportError)
    assert not isinstance(caught.value, ImportError)


def test_missing_ml_trees_extra_raises_predictive_extra_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trading_framework.infrastructure.ml.trees.xgboost import factories as xgboost_factories

    def missing_xgboost() -> object:
        raise ImportError("xgboost is not installed")

    monkeypatch.setattr(xgboost_factories, "_import_xgboost", missing_xgboost)
    spec = EstimatorSpec(
        family="xgboost.regressor",
        hyperparameters={"n_estimators": 10},
        seed=0,
        task_type=TaskType.REGRESSION,
    )
    with pytest.raises(PredictiveExtraError) as caught:
        resolve_estimator(spec)
    message = str(caught.value)
    assert "ml-trees" in message
    assert "xgboost.regressor" in message
    assert isinstance(caught.value.__cause__, ImportError)
    assert not isinstance(caught.value, ImportError)


def _is_tree_library(module_name: str) -> bool:
    roots = ("xgboost", "lightgbm", "catboost")
    return module_name in roots or any(module_name.startswith(f"{root}.") for root in roots)


def test_registry_modules_do_not_import_tree_libraries_at_module_level() -> None:
    import trading_framework.infrastructure.ml as ml_package
    import trading_framework.infrastructure.ml.registry as registry
    import trading_framework.infrastructure.ml.trees as trees_package

    trees_root = Path(trees_package.__file__).resolve().parent
    roots = (
        Path(ml_package.__file__).resolve(),
        Path(registry.__file__).resolve(),
        *sorted(trees_root.rglob("*.py")),
    )
    offenders = [
        f"{path.name}:{name}"
        for path in roots
        for name in _module_level_imported_names(path)
        if _is_tree_library(name)
    ]
    assert offenders == []


def test_registry_modules_do_not_import_sklearn_at_module_level() -> None:
    import trading_framework.infrastructure.ml as ml_package
    import trading_framework.infrastructure.ml.registry as registry
    import trading_framework.infrastructure.ml.sklearn as sklearn_package

    sklearn_root = Path(sklearn_package.__file__).resolve().parent
    roots = (
        Path(ml_package.__file__).resolve(),
        Path(registry.__file__).resolve(),
        *sorted(sklearn_root.glob("*.py")),
    )
    offenders = [
        f"{path.name}:{name}"
        for path in roots
        for name in _module_level_imported_names(path)
        if _is_sklearn(name)
    ]
    assert offenders == []
