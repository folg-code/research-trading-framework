"""Inner-training learning-curve sidecar (D-S043-16)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import trading_framework
from trading_framework.research.predictive import (
    LEARNING_CURVES_FILENAME,
    FoldLearningCurve,
    LearningCurves,
    PredictiveSpecError,
    fold_learning_curve_from_resolved_params,
    read_learning_curves,
    write_learning_curves,
)

_SOURCE = (
    Path(trading_framework.__file__).resolve().parent
    / "research"
    / "predictive"
    / "learning_curves.py"
)
_ML_LIBRARY_ROOTS = ("sklearn", "xgboost", "lightgbm", "catboost", "torch")


def _curve(*, fold_id: int = 0) -> FoldLearningCurve:
    return FoldLearningCurve(
        fold_id=fold_id,
        epochs=(1, 2, 3, 4),
        train_loss=(0.90, 0.70, 0.50, 0.45),
        validation_loss=(0.95, 0.72, 0.55, 0.58),
        stopping_epoch=3,
    )


def test_learning_curves_sidecar_round_trip(tmp_path: Path) -> None:
    payload = LearningCurves(folds=(_curve(fold_id=0), _curve(fold_id=1)))
    path = tmp_path / LEARNING_CURVES_FILENAME
    write_learning_curves(path, payload)

    restored = read_learning_curves(path)
    assert restored.to_dict()["schema_version"] == "learning_curves.v1"
    assert [fold.fold_id for fold in restored.folds] == [0, 1]
    assert restored.folds[0].stopping_epoch == 3
    assert restored.folds[0].epochs == (1, 2, 3, 4)
    assert path.name == "learning_curves.json"


def test_fold_curve_from_resolved_params_uses_one_based_epochs() -> None:
    curve = fold_learning_curve_from_resolved_params(
        2,
        {
            "inner_train_loss": [0.8, 0.6, 0.5],
            "inner_validation_loss": [0.9, 0.7, 0.65],
            "stopping_epoch": 2,
        },
    )
    assert curve is not None
    assert curve.fold_id == 2
    assert curve.epochs == (1, 2, 3)
    assert curve.train_loss == (0.8, 0.6, 0.5)
    assert curve.stopping_epoch == 2


def test_fold_curve_from_resolved_params_skips_sklearn_params() -> None:
    assert fold_learning_curve_from_resolved_params(0, {"alpha": 1.0}) is None


def test_mismatched_lengths_and_unknown_stopping_epoch_are_rejected() -> None:
    with pytest.raises(PredictiveSpecError, match="equal length"):
        FoldLearningCurve(
            fold_id=0,
            epochs=(1, 2),
            train_loss=(0.9, 0.8, 0.7),
            validation_loss=(1.0, 0.9),
            stopping_epoch=1,
        )
    with pytest.raises(PredictiveSpecError, match="not present in epochs"):
        FoldLearningCurve(
            fold_id=0,
            epochs=(1, 2, 3),
            train_loss=(0.9, 0.8, 0.7),
            validation_loss=(1.0, 0.9, 0.8),
            stopping_epoch=9,
        )


def test_learning_curves_module_does_not_import_ml_libraries() -> None:
    source = _SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in _ML_LIBRARY_ROOTS
    )
    assert "json" in imported
