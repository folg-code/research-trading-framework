"""Declared purged walk-forward split policy (no fold planner)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.time.models.timeframe import Timeframe


class PurgedWalkForwardSplitMode(StrEnum):
    """Train-window growth policy between chronological test folds."""

    ROLLING = "ROLLING"
    EXPANDING = "EXPANDING"


@dataclass(frozen=True, slots=True)
class PurgedWalkForwardSplitSpec:
    """Declarative purged + embargoed walk-forward policy.

    ``test_span`` and ``embargo_span`` are bar ``Timeframe`` durations (minutes,
    hours, or days), matching the rest of the research YAML language. Fold
    assignment is not computed here; this type is hashed with the study spec so
    a later planner cannot silently change the declared policy.
    """

    mode: PurgedWalkForwardSplitMode
    fold_count: int
    test_span: Timeframe
    embargo_span: Timeframe
    min_train_rows: int

    def __post_init__(self) -> None:
        if self.fold_count < 1:
            msg = "fold_count must be at least 1"
            raise PredictiveSpecError(msg)
        if self.min_train_rows < 1:
            msg = "min_train_rows must be at least 1"
            raise PredictiveSpecError(msg)
        if self.test_span.is_event_level:
            msg = "test_span must be a bar duration, not tick"
            raise PredictiveSpecError(msg)
        if self.test_span.total_seconds <= 0:
            msg = "test_span must be a positive duration"
            raise PredictiveSpecError(msg)
        if self.embargo_span.is_event_level:
            msg = "embargo_span must be a bar duration, not tick"
            raise PredictiveSpecError(msg)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "fold_count": self.fold_count,
            "test_span": self.test_span.value,
            "embargo_span": self.embargo_span.value,
            "min_train_rows": self.min_train_rows,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PurgedWalkForwardSplitSpec:
        try:
            mode = PurgedWalkForwardSplitMode(str(payload["mode"]))
        except KeyError as exc:
            msg = f"split spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        except ValueError as exc:
            msg = f"invalid split mode: {payload.get('mode')!r}"
            raise PredictiveSpecError(msg) from exc
        try:
            return cls(
                mode=mode,
                fold_count=_require_int(payload["fold_count"], field_name="fold_count"),
                test_span=Timeframe(str(payload["test_span"])),
                embargo_span=Timeframe(str(payload["embargo_span"])),
                min_train_rows=_require_int(payload["min_train_rows"], field_name="min_train_rows"),
            )
        except KeyError as exc:
            msg = f"split spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        except ValidationError as exc:
            if isinstance(exc, PredictiveSpecError):
                raise
            raise PredictiveSpecError(str(exc)) from exc


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value
