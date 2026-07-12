"""Polars backward as-of alignment for multitimeframe batch analysis."""

from __future__ import annotations

import math
from datetime import datetime

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


def align_values_to_evaluation_grid(
    *,
    values: tuple[float, ...],
    available_at: tuple[datetime, ...],
    evaluation_timestamps: tuple[datetime, ...],
    policy: AlignmentPolicy,
) -> tuple[float, ...]:
    """Align one HTF value series onto an evaluation grid via backward ``join_asof``."""
    if policy != AlignmentPolicy.LAST_CLOSED_BAR:
        msg = f"Sprint 004 MVP implements {AlignmentPolicy.LAST_CLOSED_BAR.value} only"
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
    return align_values_to_evaluation_grid(
        values=series.values,
        available_at=series.available_at,
        evaluation_timestamps=evaluation_timestamps,
        policy=policy,
    )
