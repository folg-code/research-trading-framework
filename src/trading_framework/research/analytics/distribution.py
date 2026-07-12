"""Distribution summaries for Signal Research analytics."""

from __future__ import annotations

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metrics import aggregate_distribution_metrics
from trading_framework.research.analytics.schemas import (
    empty_distribution_summaries,
    validate_distribution_summaries,
)


def compute_distribution_summary(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    min_sample_size: int,
    interpretation_min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter,
) -> pl.DataFrame:
    """Return one-row distribution summary for one run x horizon."""
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    complete = outcome_filter.filter_for_aggregates(subset)
    sample_complete = len(complete)
    metrics_computable = sample_complete >= min_sample_size
    metrics_interpretable = sample_complete >= interpretation_min_sample_size

    if metrics_computable:
        distribution = aggregate_distribution_metrics(complete)
    else:
        distribution = {
            "forward_return_p10": None,
            "forward_return_p25": None,
            "forward_return_p75": None,
            "forward_return_p90": None,
            "forward_return_std": None,
            "forward_return_min": None,
            "forward_return_max": None,
        }

    run_id = str(subset.row(0, named=True)["run_id"]) if len(subset) else ""
    summary = pl.DataFrame(
        {
            "run_id": [run_id],
            "horizon_bars": [horizon_bars],
            "sample_size_complete": [sample_complete],
            "minimum_required": [min_sample_size],
            "interpretation_minimum_required": [interpretation_min_sample_size],
            "metrics_computable": [metrics_computable],
            "metrics_interpretable": [metrics_interpretable],
            "forward_return_p10": [distribution["forward_return_p10"]],
            "forward_return_p25": [distribution["forward_return_p25"]],
            "forward_return_p75": [distribution["forward_return_p75"]],
            "forward_return_p90": [distribution["forward_return_p90"]],
            "forward_return_std": [distribution["forward_return_std"]],
            "forward_return_min": [distribution["forward_return_min"]],
            "forward_return_max": [distribution["forward_return_max"]],
        },
        schema=empty_distribution_summaries().schema,
    )
    validate_distribution_summaries(summary)
    return summary


def summarize_distribution_summaries(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    min_sample_size: int,
    interpretation_min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter,
) -> pl.DataFrame:
    """Return distribution summary rows for each requested horizon."""
    if not horizons:
        empty = empty_distribution_summaries()
        validate_distribution_summaries(empty)
        return empty

    summaries = [
        compute_distribution_summary(
            frame,
            horizon_bars=horizon,
            min_sample_size=min_sample_size,
            interpretation_min_sample_size=interpretation_min_sample_size,
            outcome_filter=outcome_filter,
        )
        for horizon in horizons
    ]
    combined = pl.concat(summaries)
    validate_distribution_summaries(combined)
    return combined
