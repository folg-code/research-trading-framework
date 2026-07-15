"""Walk-forward fold planning contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.models.time_range import TimeRange


class WalkForwardWindowMode(StrEnum):
    """Train window growth policy between folds."""

    ROLLING = "ROLLING"
    EXPANDING = "EXPANDING"


@dataclass(frozen=True, slots=True)
class WalkForwardSpec:
    """Declarative walk-forward window policy."""

    window_mode: WalkForwardWindowMode
    train_duration_seconds: int
    oos_duration_seconds: int
    step_duration_seconds: int
    selection_metric: str = "net_pnl"

    def __post_init__(self) -> None:
        if self.train_duration_seconds <= 0:
            msg = "train_duration_seconds must be positive"
            raise ValidationError(msg)
        if self.oos_duration_seconds <= 0:
            msg = "oos_duration_seconds must be positive"
            raise ValidationError(msg)
        if self.step_duration_seconds <= 0:
            msg = "step_duration_seconds must be positive"
            raise ValidationError(msg)

    @property
    def train_duration(self) -> timedelta:
        return timedelta(seconds=self.train_duration_seconds)

    @property
    def oos_duration(self) -> timedelta:
        return timedelta(seconds=self.oos_duration_seconds)

    @property
    def step_duration(self) -> timedelta:
        return timedelta(seconds=self.step_duration_seconds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_mode": self.window_mode.value,
            "train_duration_seconds": self.train_duration_seconds,
            "oos_duration_seconds": self.oos_duration_seconds,
            "step_duration_seconds": self.step_duration_seconds,
            "selection_metric": self.selection_metric,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardSpec:
        return cls(
            window_mode=WalkForwardWindowMode(str(payload["window_mode"])),
            train_duration_seconds=int(payload["train_duration_seconds"]),
            oos_duration_seconds=int(payload["oos_duration_seconds"]),
            step_duration_seconds=int(payload["step_duration_seconds"]),
            selection_metric=str(payload.get("selection_metric", "net_pnl")),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    """One train/OOS split in chronological order."""

    fold_id: str
    fold_index: int
    train_range: TimeRange
    oos_range: TimeRange

    def to_dict(self) -> dict[str, Any]:
        return {
            "fold_id": self.fold_id,
            "fold_index": self.fold_index,
            "train_range_start": self.train_range.start.isoformat(),
            "train_range_end": self.train_range.end.isoformat(),
            "oos_range_start": self.oos_range.start.isoformat(),
            "oos_range_end": self.oos_range.end.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardFold:
        return cls(
            fold_id=str(payload["fold_id"]),
            fold_index=int(payload["fold_index"]),
            train_range=TimeRange(
                start=datetime.fromisoformat(str(payload["train_range_start"])),
                end=datetime.fromisoformat(str(payload["train_range_end"])),
            ),
            oos_range=TimeRange(
                start=datetime.fromisoformat(str(payload["oos_range_start"])),
                end=datetime.fromisoformat(str(payload["oos_range_end"])),
            ),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardFoldResult:
    """Execution outcome for one walk-forward fold."""

    fold: WalkForwardFold
    status: str
    selected_config_id: str | None = None
    selected_parameter_overrides: dict[str, str] | None = None
    selected_strategy_run_id: str | None = None
    train_net_pnl: str | None = None
    oos_strategy_run_id: str | None = None
    oos_net_pnl: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "fold": self.fold.to_dict(),
            "status": self.status,
        }
        if self.selected_config_id is not None:
            payload["selected_config_id"] = self.selected_config_id
        if self.selected_parameter_overrides is not None:
            payload["selected_parameter_overrides"] = self.selected_parameter_overrides
        if self.selected_strategy_run_id is not None:
            payload["selected_strategy_run_id"] = self.selected_strategy_run_id
        if self.train_net_pnl is not None:
            payload["train_net_pnl"] = self.train_net_pnl
        if self.oos_strategy_run_id is not None:
            payload["oos_strategy_run_id"] = self.oos_strategy_run_id
        if self.oos_net_pnl is not None:
            payload["oos_net_pnl"] = self.oos_net_pnl
        if self.error_message is not None:
            payload["error_message"] = self.error_message
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardFoldResult:
        return cls(
            fold=WalkForwardFold.from_dict(payload["fold"]),
            status=str(payload["status"]),
            selected_config_id=(
                str(payload["selected_config_id"])
                if payload.get("selected_config_id") is not None
                else None
            ),
            selected_parameter_overrides=(
                {
                    str(key): str(value)
                    for key, value in payload["selected_parameter_overrides"].items()
                }
                if payload.get("selected_parameter_overrides") is not None
                else None
            ),
            selected_strategy_run_id=(
                str(payload["selected_strategy_run_id"])
                if payload.get("selected_strategy_run_id") is not None
                else None
            ),
            train_net_pnl=(
                str(payload["train_net_pnl"]) if payload.get("train_net_pnl") is not None else None
            ),
            oos_strategy_run_id=(
                str(payload["oos_strategy_run_id"])
                if payload.get("oos_strategy_run_id") is not None
                else None
            ),
            oos_net_pnl=(
                str(payload["oos_net_pnl"]) if payload.get("oos_net_pnl") is not None else None
            ),
            error_message=(
                str(payload["error_message"]) if payload.get("error_message") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardResults:
    """Persisted walk-forward execution state."""

    experiment_id: str
    folds: tuple[WalkForwardFoldResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "folds": [fold.to_dict() for fold in self.folds],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardResults:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            folds=tuple(WalkForwardFoldResult.from_dict(fold) for fold in payload["folds"]),
        )


@dataclass(frozen=True, slots=True)
class WalkForwardFoldPlan:
    """Persisted fold schedule for one experiment."""

    experiment_id: str
    folds: tuple[WalkForwardFold, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "folds": [fold.to_dict() for fold in self.folds],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WalkForwardFoldPlan:
        return cls(
            experiment_id=str(payload["experiment_id"]),
            folds=tuple(WalkForwardFold.from_dict(fold) for fold in payload["folds"]),
        )


def timeframe_bar_step(timeframe: str) -> timedelta:
    """Return one bar step for a supported timeframe string."""
    if timeframe == "1m":
        return timedelta(minutes=1)
    msg = f"unsupported walk-forward timeframe: {timeframe}"
    raise ValidationError(msg)


def plan_walk_forward_folds(
    *,
    overall_range: TimeRange,
    spec: WalkForwardSpec,
    bar_step: timedelta,
) -> tuple[WalkForwardFold, ...]:
    """Plan non-overlapping train/OOS folds over one UTC range."""
    folds: list[WalkForwardFold] = []
    fold_index = 0
    anchor = overall_range.start

    if spec.window_mode is WalkForwardWindowMode.ROLLING:
        train_start = anchor
        while True:
            train_end = train_start + spec.train_duration
            oos_start = train_end + bar_step
            oos_end = oos_start + spec.oos_duration
            if oos_end > overall_range.end:
                break
            if train_start < overall_range.start:
                break
            folds.append(
                _build_fold(
                    fold_index=fold_index,
                    train_start=train_start,
                    train_end=train_end,
                    oos_start=oos_start,
                    oos_end=oos_end,
                )
            )
            fold_index += 1
            train_start += spec.step_duration
    else:
        train_start = anchor
        train_end = anchor + spec.train_duration
        while True:
            oos_start = train_end + bar_step
            oos_end = oos_start + spec.oos_duration
            if oos_end > overall_range.end:
                break
            folds.append(
                _build_fold(
                    fold_index=fold_index,
                    train_start=train_start,
                    train_end=train_end,
                    oos_start=oos_start,
                    oos_end=oos_end,
                )
            )
            fold_index += 1
            train_end += spec.step_duration

    if not folds:
        msg = "walk-forward spec produced no folds for requested range"
        raise ValidationError(msg)
    return tuple(folds)


def _build_fold(
    *,
    fold_index: int,
    train_start: datetime,
    train_end: datetime,
    oos_start: datetime,
    oos_end: datetime,
) -> WalkForwardFold:
    return WalkForwardFold(
        fold_id=f"fold_{fold_index:03d}",
        fold_index=fold_index,
        train_range=TimeRange(start=_ensure_utc(train_start), end=_ensure_utc(train_end)),
        oos_range=TimeRange(start=_ensure_utc(oos_start), end=_ensure_utc(oos_end)),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
