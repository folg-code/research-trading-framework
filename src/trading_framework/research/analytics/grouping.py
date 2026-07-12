"""Time-derived grouping dimensions for Signal Research analytics."""

from __future__ import annotations

from typing import Any, assert_never

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.aggregates import compute_run_summary
from trading_framework.research.analytics.dimensions import (
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import DEFAULT_TIME_OF_DAY_BUCKET_MINUTES
from trading_framework.research.analytics.schemas import (
    empty_grouped_summaries,
    validate_grouped_summaries,
)
from trading_framework.time.sessions import CmeEsRthSessionResolver
from trading_framework.time.sessions.constants import ES_RTH_SESSION_ID


def _timestamp_column(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
) -> pl.Series:
    column = basis.value
    if column not in frame.columns:
        msg = f"timestamp basis column missing: {column}"
        raise ValidationError(msg)
    return frame[column]


def _with_rth_membership(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
) -> pl.DataFrame:
    timestamps = _timestamp_column(frame, basis=basis)
    resolved = CmeEsRthSessionResolver().resolve(timestamps)
    membership = [
        "RTH" if session_id == ES_RTH_SESSION_ID else "OUTSIDE_RTH"
        for session_id in resolved["session_id"].to_list()
    ]
    return frame.with_columns(pl.Series("rth_membership", membership))


def _with_time_of_day(
    frame: pl.DataFrame,
    *,
    basis: AnalyticsTimestampBasis,
    bucket_minutes: int = DEFAULT_TIME_OF_DAY_BUCKET_MINUTES,
) -> pl.DataFrame:
    if bucket_minutes != DEFAULT_TIME_OF_DAY_BUCKET_MINUTES:
        msg = f"MVP supports {DEFAULT_TIME_OF_DAY_BUCKET_MINUTES}-minute buckets only"
        raise ValidationError(msg)
    ts_col = basis.value
    return frame.with_columns(
        pl.col(ts_col)
        .dt.convert_time_zone("America/New_York")
        .dt.truncate("1h")
        .dt.strftime("%H:00")
        .alias("time_of_day_bucket")
    )


def _assign_group_column(
    frame: pl.DataFrame,
    *,
    dimension: GroupDimension,
    timestamp_basis: AnalyticsTimestampBasis,
) -> tuple[pl.DataFrame, str]:
    if dimension is GroupDimension.HORIZON:
        working = frame.with_columns(pl.col("horizon_bars").cast(pl.String).alias("group_value"))
        return working, "group_value"
    if dimension is GroupDimension.RTH_MEMBERSHIP:
        working = _with_rth_membership(frame, basis=timestamp_basis)
        return working, "rth_membership"
    if dimension is GroupDimension.TIME_OF_DAY:
        working = _with_time_of_day(frame, basis=timestamp_basis)
        return working, "time_of_day_bucket"
    if dimension is GroupDimension.CONTEXT_MET:
        working = frame.with_columns(
            pl.col("context_met_at_available_at").cast(pl.String).alias("group_value")
        )
        return working, "group_value"
    if dimension is GroupDimension.CALENDAR_MONTH:
        ts = _timestamp_column(frame, basis=timestamp_basis)
        working = frame.with_columns(ts.dt.strftime("%Y-%m").alias("group_value"))
        return working, "group_value"
    assert_never(dimension)


def compute_grouped_summary(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    dimension: GroupDimension,
    min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter,
    timestamp_basis: AnalyticsTimestampBasis = AnalyticsTimestampBasis.AVAILABLE_AT,
) -> pl.DataFrame:
    """Return grouped summary rows for one horizon and dimension."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    working, group_col = _assign_group_column(
        subset,
        dimension=dimension,
        timestamp_basis=timestamp_basis,
    )

    rows: list[dict[str, Any]] = []
    for group_value in working[group_col].unique().sort().to_list():
        group_frame = working.filter(pl.col(group_col) == group_value)
        summary = compute_run_summary(
            group_frame,
            horizon_bars=horizon_bars,
            min_sample_size=min_sample_size,
            outcome_filter=outcome_filter,
        ).row(0, named=True)
        rows.append(
            {
                "run_id": summary["run_id"],
                "research_scope": summary["research_scope"],
                "horizon_bars": summary["horizon_bars"],
                "group_dimension": dimension.value,
                "group_value": str(group_value),
                "sample_size_total": summary["sample_size_total"],
                "sample_size_complete": summary["sample_size_complete"],
                "sample_size_incomplete": summary["sample_size_incomplete"],
                "metrics_eligible": summary["metrics_eligible"],
                "forward_return_mean": summary["forward_return_mean"],
                "forward_return_median": summary["forward_return_median"],
                "hit_rate": summary["hit_rate"],
                "mfe_mean": summary["mfe_mean"],
                "mfe_median": summary["mfe_median"],
                "mae_mean": summary["mae_mean"],
                "mae_median": summary["mae_median"],
            }
        )

    grouped = (
        pl.DataFrame(rows, schema=empty_grouped_summaries().schema)
        if rows
        else empty_grouped_summaries()
    )
    validate_grouped_summaries(grouped)
    return grouped


def summarize_grouped_summaries(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    group_by: tuple[GroupDimension, ...],
    min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter,
    timestamp_basis: AnalyticsTimestampBasis,
) -> pl.DataFrame | None:
    """Return grouped summaries for all requested horizons and dimensions."""
    if not group_by:
        return None

    parts: list[pl.DataFrame] = []
    for horizon in horizons:
        for dimension in group_by:
            parts.append(
                compute_grouped_summary(
                    frame,
                    horizon_bars=horizon,
                    dimension=dimension,
                    min_sample_size=min_sample_size,
                    outcome_filter=outcome_filter,
                    timestamp_basis=timestamp_basis,
                )
            )

    if not parts:
        empty = empty_grouped_summaries()
        validate_grouped_summaries(empty)
        return empty

    combined = pl.concat(parts)
    validate_grouped_summaries(combined)
    return combined
