"""Inner-training learning curves for Predictive Research (D-S043-16).

Library-free: framework contracts only. Curves come from the inner-train /
inner-validation early-stopping run recorded on ``describe().resolved_params``,
not from a TEST-supervised refit.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_framework.research.predictive.errors import PredictiveSpecError

LEARNING_CURVES_FILENAME = "learning_curves.json"
LEARNING_CURVES_SCHEMA_VERSION = "learning_curves.v1"


@dataclass(frozen=True, slots=True)
class FoldLearningCurve:
    """Train and inner-validation loss per epoch for one outer fold."""

    fold_id: int
    epochs: tuple[int, ...]
    train_loss: tuple[float, ...]
    validation_loss: tuple[float, ...]
    stopping_epoch: int

    def __post_init__(self) -> None:
        n_epochs = len(self.epochs)
        if n_epochs == 0:
            msg = "learning curve epochs must be non-empty"
            raise PredictiveSpecError(msg)
        if len(self.train_loss) != n_epochs or len(self.validation_loss) != n_epochs:
            msg = "learning curve epochs, train_loss, and validation_loss must have equal length"
            raise PredictiveSpecError(msg)
        if self.stopping_epoch not in self.epochs:
            msg = (
                f"stopping_epoch {self.stopping_epoch} is not present in epochs {list(self.epochs)}"
            )
            raise PredictiveSpecError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "epochs": list(self.epochs),
            "train_loss": list(self.train_loss),
            "validation_loss": list(self.validation_loss),
            "stopping_epoch": self.stopping_epoch,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FoldLearningCurve:
        epochs = _int_tuple(payload.get("epochs"), "epochs")
        return cls(
            fold_id=_require_int(payload.get("fold_id"), field_name="fold_id"),
            epochs=epochs,
            train_loss=_float_tuple(payload.get("train_loss"), "train_loss"),
            validation_loss=_float_tuple(payload.get("validation_loss"), "validation_loss"),
            stopping_epoch=_require_int(payload.get("stopping_epoch"), field_name="stopping_epoch"),
        )


@dataclass(frozen=True, slots=True)
class LearningCurves:
    """Sidecar payload written as ``learning_curves.json`` (D-S043-16)."""

    folds: tuple[FoldLearningCurve, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": LEARNING_CURVES_SCHEMA_VERSION,
            "folds": [fold.to_dict() for fold in self.folds],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LearningCurves:
        raw_folds = payload.get("folds")
        if not isinstance(raw_folds, Sequence) or isinstance(raw_folds, (str, bytes)):
            msg = "learning curves folds must be a sequence"
            raise PredictiveSpecError(msg)
        folds: list[FoldLearningCurve] = []
        for item in raw_folds:
            if not isinstance(item, Mapping):
                msg = "learning curve fold entries must be mappings"
                raise PredictiveSpecError(msg)
            folds.append(FoldLearningCurve.from_dict(item))
        return cls(folds=tuple(folds))


def fold_learning_curve_from_resolved_params(
    fold_id: int,
    resolved_params: Mapping[str, Any],
) -> FoldLearningCurve | None:
    """Build a fold curve from adapter ``describe().resolved_params``, or skip.

    Missing inner-loss keys (sklearn / tree families) return ``None`` so the
    report panel can skip instead of failing.
    """
    train_raw = resolved_params.get("inner_train_loss")
    validation_raw = resolved_params.get("inner_validation_loss")
    stopping_raw = resolved_params.get("stopping_epoch")
    if train_raw is None or validation_raw is None or stopping_raw is None:
        return None
    train_loss = _float_tuple(train_raw, "inner_train_loss")
    validation_loss = _float_tuple(validation_raw, "inner_validation_loss")
    epochs_raw = resolved_params.get("epochs")
    if epochs_raw is None:
        epochs = tuple(range(1, len(train_loss) + 1))
    else:
        epochs = _int_tuple(epochs_raw, "epochs")
    return FoldLearningCurve(
        fold_id=fold_id,
        epochs=epochs,
        train_loss=train_loss,
        validation_loss=validation_loss,
        stopping_epoch=_require_int(stopping_raw, field_name="stopping_epoch"),
    )


def write_learning_curves(path: Path, curves: LearningCurves) -> None:
    """Persist ``learning_curves.json`` next to a predictive run."""
    path.write_text(json.dumps(curves.to_dict(), indent=2) + "\n", encoding="utf-8")


def read_learning_curves(path: Path) -> LearningCurves:
    """Load a ``learning_curves.json`` sidecar."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        msg = "learning curves file must contain a mapping"
        raise PredictiveSpecError(msg)
    return LearningCurves.from_dict(payload)


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value


def _int_tuple(value: object, field_name: str) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        msg = f"{field_name} must be a sequence of integers"
        raise PredictiveSpecError(msg)
    return tuple(_require_int(item, field_name=field_name) for item in value)


def _float_tuple(value: object, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        msg = f"{field_name} must be a sequence of numbers"
        raise PredictiveSpecError(msg)
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            msg = f"{field_name} must be a sequence of numbers"
            raise PredictiveSpecError(msg)
        numbers.append(float(item))
    return tuple(numbers)
