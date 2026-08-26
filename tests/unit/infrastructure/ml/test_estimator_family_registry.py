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
