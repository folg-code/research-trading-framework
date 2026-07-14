"""Polars backward as-of alignment for multitimeframe batch analysis."""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.result import OutputSeries
from trading_framework.time.models.timeframe import Timeframe


def needs_alignment(
    *,
    computation_timeframe: Timeframe,
    evaluation_timeframe: Timeframe,
) -> bool:
    """Return whether a component result must be aligned to the evaluation grid."""
    return computation_timeframe != evaluation_timeframe


def _timestamps_to_ns(timestamps: tuple[datetime, ...]) -> np.ndarray:
    return np.fromiter(
        (int(timestamp.timestamp() * 1_000_000_000) for timestamp in timestamps),
        dtype=np.int64,
        count=len(timestamps),
    )


def _is_active_event(value: float, inactive_event_fill: float) -> bool:
    if math.isnan(value):
        return False
    if math.isnan(inactive_event_fill):
        return True
    return value != inactive_event_fill


def align_event_at_available(
    *,
    values: tuple[float, ...],
    available_at: tuple[datetime, ...],
    evaluation_timestamps: tuple[datetime, ...],
    inactive_event_fill: float,
) -> tuple[float, ...]:
    """Project each HTF event onto the first evaluation bar at or after ``available_at``."""
    if len(values) != len(available_at):
        msg = "values and available_at must share the same length"
        raise ValidationError(msg)
    if not evaluation_timestamps:
        return ()

    evaluation_ns = _timestamps_to_ns(evaluation_timestamps)
    available_ns = _timestamps_to_ns(available_at)
    values_arr = np.asarray(values, dtype=np.float64)
    aligned = np.full(len(evaluation_timestamps), inactive_event_fill, dtype=np.float64)

    for index, value in enumerate(values_arr):
        if not _is_active_event(float(value), inactive_event_fill):
            continue
        target_index = int(np.searchsorted(evaluation_ns, available_ns[index], side="left"))
        if target_index < len(evaluation_ns):
            aligned[target_index] = value

    return tuple(float(value) for value in aligned)


def align_values_to_evaluation_grid(
    *,
    values: tuple[float, ...],
    available_at: tuple[datetime, ...],
    evaluation_timestamps: tuple[datetime, ...],
    policy: AlignmentPolicy,
    inactive_event_fill: float | None = None,
) -> tuple[float, ...]:
    """Align one HTF value series onto an evaluation grid."""
    if policy is AlignmentPolicy.EVENT_AT_AVAILABLE:
        if inactive_event_fill is None:
            msg = "EVENT_AT_AVAILABLE alignment requires inactive_event_fill"
            raise ValidationError(msg)
        return align_event_at_available(
            values=values,
            available_at=available_at,
            evaluation_timestamps=evaluation_timestamps,
            inactive_event_fill=inactive_event_fill,
        )
    if policy != AlignmentPolicy.LAST_CLOSED_BAR:
        msg = (
            f"Sprint 005 MVP implements {AlignmentPolicy.LAST_CLOSED_BAR.value} and "
            f"{AlignmentPolicy.EVENT_AT_AVAILABLE.value}"
        )
        raise ValidationError(msg)
    if len(values) != len(available_at):
        msg = "values and available_at must share the same length"
        raise ValidationError(msg)
    if not evaluation_timestamps:
        return ()

    htf = pl.DataFrame({"available_at": list(available_at), "value": list(values)})
    valid = htf.filter(pl.col("value").is_not_nan())
    ltf = pl.DataFrame({"evaluation_at": list(evaluation_timestamps)})

    if valid.is_empty():
        return tuple(math.nan for _ in evaluation_timestamps)

    aligned = ltf.sort("evaluation_at").join_asof(
        valid.sort("available_at"),
        left_on="evaluation_at",
        right_on="available_at",
        strategy="backward",
    )
    return tuple(
        float(value)
        if value is not None and not (isinstance(value, float) and math.isnan(value))
        else math.nan
        for value in aligned["value"].to_list()
    )


def align_output_series(
    series: OutputSeries,
    *,
    evaluation_timestamps: tuple[datetime, ...],
    policy: AlignmentPolicy,
) -> tuple[float, ...]:
    """Align one output series when ``available_at`` metadata is present."""
    if series.available_at is None:
        msg = "alignment requires per-bar available_at metadata on the output series"
        raise ValidationError(msg)
    inactive_event_fill = None
    if policy is AlignmentPolicy.EVENT_AT_AVAILABLE:
        if series.inactive_event_fill is None:
            msg = "EVENT_AT_AVAILABLE alignment requires inactive_event_fill on OutputSeries"
            raise ValidationError(msg)
        inactive_event_fill = series.inactive_event_fill
    return align_values_to_evaluation_grid(
        values=series.values,
        available_at=series.available_at,
        evaluation_timestamps=evaluation_timestamps,
        policy=policy,
        inactive_event_fill=inactive_event_fill,
    )
