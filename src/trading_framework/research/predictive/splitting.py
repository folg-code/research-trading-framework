"""Purged walk-forward split policy and fold-role planner."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.errors import (
    PredictiveMatrixError,
    PredictiveSpecError,
)
from trading_framework.time.models.timeframe import Timeframe

_REQUIRED_TIME_COLUMNS = ("available_at", "label_end_at")


class PurgedWalkForwardSplitMode(StrEnum):
    """Train-window growth policy between chronological test folds."""

    ROLLING = "ROLLING"
    EXPANDING = "EXPANDING"


class FoldRole(StrEnum):
    """Persisted role of a labelled row inside one walk-forward fold."""

    TRAIN = "TRAIN"
    TEST = "TEST"
    PURGED = "PURGED"
    EMBARGOED = "EMBARGOED"


@dataclass(frozen=True, slots=True)
class PurgedWalkForwardSplitSpec:
    """Declarative purged + embargoed walk-forward policy.

    ``test_span`` and ``embargo_span`` are bar ``Timeframe`` durations (minutes,
    hours, or days), matching the rest of the research YAML language. This type
    is hashed with the study spec; ``assign_purged_walk_forward_folds`` applies
    the policy to labelled rows.
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


def assign_purged_walk_forward_folds(
    rows: pl.DataFrame,
    spec: PurgedWalkForwardSplitSpec,
) -> pl.DataFrame:
    """Assign TRAIN / TEST / PURGED / EMBARGOED roles in long format.

    Each labelled row is duplicated once per fold it participates in. Test
    windows are chronological, non-overlapping, and placed from the end of
    ``available_at`` using datetime arithmetic (not a bar grid). Consecutive
    tests are separated by ``embargo_span`` so expanding later folds cannot
    train on the held-out gap after an earlier test.
    """
    ordered = _ordered_labelled_rows(rows)
    windows = _fold_windows(ordered, spec)
    assigned_folds = [
        _assign_one_fold(
            ordered,
            window=window,
            previous=windows[:index],
            min_train_rows=spec.min_train_rows,
        )
        for index, window in enumerate(windows)
    ]
    assigned = pl.concat(assigned_folds, how="vertical")
    sort_keys = ["fold_id", "available_at"]
    if "entity_id" in assigned.columns:
        sort_keys.append("entity_id")
    if "horizon_bars" in assigned.columns:
        sort_keys.append("horizon_bars")
    return assigned.sort(sort_keys)


def _require_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field_name} must be an integer"
        raise PredictiveSpecError(msg)
    return value


@dataclass(frozen=True, slots=True)
class _FoldWindow:
    fold_id: int
    test_lower: datetime
    test_end: datetime
    embargo_end: datetime
    train_start: datetime

    def contains_test(self, timestamp: pl.Expr) -> pl.Expr:
        return (timestamp > self.test_lower) & (timestamp <= self.test_end)

    def contains_embargo(self, timestamp: pl.Expr) -> pl.Expr:
        return (timestamp > self.test_end) & (timestamp <= self.embargo_end)

    def contains_train_candidate(self, timestamp: pl.Expr) -> pl.Expr:
        return (timestamp >= self.train_start) & (timestamp <= self.test_lower)


def _ordered_labelled_rows(rows: pl.DataFrame) -> pl.DataFrame:
    missing = [name for name in _REQUIRED_TIME_COLUMNS if name not in rows.columns]
    if missing:
        msg = f"labelled rows missing required column: {missing[0]}"
        raise PredictiveMatrixError(msg)
    if rows.height == 0:
        msg = "labelled rows are empty; cannot assign folds"
        raise PredictiveMatrixError(msg)
    for name in _REQUIRED_TIME_COLUMNS:
        if rows.get_column(name).null_count() > 0:
            msg = f"{name} must not be null"
            raise PredictiveMatrixError(msg)
    sort_keys = ["available_at"]
    if "entity_id" in rows.columns:
        sort_keys.append("entity_id")
    if "horizon_bars" in rows.columns:
        sort_keys.append("horizon_bars")
    return rows.sort(sort_keys)


def _fold_windows(rows: pl.DataFrame, spec: PurgedWalkForwardSplitSpec) -> tuple[_FoldWindow, ...]:
    t_min = rows.get_column("available_at").min()
    t_max = rows.get_column("available_at").max()
    if not isinstance(t_min, datetime) or not isinstance(t_max, datetime):
        msg = "available_at must be a datetime column"
        raise PredictiveMatrixError(msg)
    test_span = timedelta(seconds=spec.test_span.total_seconds)
    embargo_span = timedelta(seconds=spec.embargo_span.total_seconds)
    stride = test_span + embargo_span
    first_test_lower = t_max - ((spec.fold_count - 1) * stride) - test_span
    if first_test_lower < t_min:
        msg = (
            "available_at range is too short to place "
            f"{spec.fold_count} test windows of {spec.test_span.value} with embargo "
            f"{spec.embargo_span.value} and any training history"
        )
        raise PredictiveMatrixError(msg)
    initial_train_duration = first_test_lower - t_min
    windows: list[_FoldWindow] = []
    for fold_id in range(spec.fold_count):
        test_end = t_max - ((spec.fold_count - 1 - fold_id) * stride)
        test_lower = test_end - test_span
        if spec.mode is PurgedWalkForwardSplitMode.EXPANDING:
            train_start = t_min
        else:
            train_start = test_lower - initial_train_duration
        windows.append(
            _FoldWindow(
                fold_id=fold_id,
                test_lower=test_lower,
                test_end=test_end,
                embargo_end=test_end + embargo_span,
                train_start=train_start,
            )
        )
    return tuple(windows)


def _assign_one_fold(
    rows: pl.DataFrame,
    *,
    window: _FoldWindow,
    previous: Sequence[_FoldWindow],
    min_train_rows: int,
) -> pl.DataFrame:
    available = pl.col("available_at")
    label_end = pl.col("label_end_at")
    in_prior_embargo = pl.lit(False)
    for prior in previous:
        in_prior_embargo = in_prior_embargo | prior.contains_embargo(available)
    role = (
        pl.when(window.contains_test(available))
        .then(pl.lit(FoldRole.TEST.value))
        .when(window.contains_embargo(available))
        .then(pl.lit(FoldRole.EMBARGOED.value))
        .when(window.contains_train_candidate(available) & window.contains_test(label_end))
        .then(pl.lit(FoldRole.PURGED.value))
        .when(window.contains_train_candidate(available) & in_prior_embargo)
        .then(pl.lit(FoldRole.EMBARGOED.value))
        .when(window.contains_train_candidate(available))
        .then(pl.lit(FoldRole.TRAIN.value))
    )
    assigned = rows.with_columns(
        pl.lit(window.fold_id).cast(pl.Int64).alias("fold_id"),
        role.alias("fold_role"),
    ).filter(pl.col("fold_role").is_not_null())
    test_count = assigned.filter(pl.col("fold_role") == FoldRole.TEST.value).height
    if test_count == 0:
        msg = f"fold {window.fold_id} has no TEST rows in the available_at range"
        raise PredictiveMatrixError(msg)
    train_count = assigned.filter(pl.col("fold_role") == FoldRole.TRAIN.value).height
    if train_count < min_train_rows:
        msg = (
            f"fold {window.fold_id} has {train_count} TRAIN rows after purge/embargo, "
            f"but min_train_rows is {min_train_rows}"
        )
        raise PredictiveMatrixError(msg)
    return assigned
