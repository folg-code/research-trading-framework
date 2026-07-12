"""Run-level aggregate metrics for Signal Research analytics."""

from __future__ import annotations

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metrics import aggregate_complete_metrics
from trading_framework.research.analytics.schemas import (
    empty_run_summaries,
    validate_run_summaries,
)


def compute_run_summary(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter | None = None,
) -> pl.DataFrame:
    """Return one-row RunSummary ``DataFrame`` for one run x horizon."""
    aggregate_filter = outcome_filter or OutcomeAnalyticsFilter.complete_only()
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    sample_total = len(subset)
    complete = aggregate_filter.filter_for_aggregates(subset)
    sample_complete = len(complete)
    sample_incomplete = sample_total - sample_complete
    completion_rate = sample_complete / sample_total if sample_total else 0.0
    metrics_eligible = sample_complete >= min_sample_size

    metrics: dict[str, float | None]
    if metrics_eligible:
        metrics = aggregate_complete_metrics(complete)
    else:
        metrics = {
            "forward_return_mean": None,
            "forward_return_median": None,
            "hit_rate": None,
            "mfe_mean": None,
            "mfe_median": None,
            "mae_mean": None,
            "mae_median": None,
        }

    run_id = str(subset.row(0, named=True)["run_id"]) if sample_total else ""
    scope = str(subset.row(0, named=True)["research_scope"]) if sample_total else ""
    summary = pl.DataFrame(
        {
            "run_id": [run_id],
            "research_scope": [scope],
            "horizon_bars": [horizon_bars],
            "sample_size_total": [sample_total],
            "sample_size_complete": [sample_complete],
            "sample_size_incomplete": [sample_incomplete],
            "completion_rate": [completion_rate],
            "minimum_required": [min_sample_size],
            "metrics_eligible": [metrics_eligible],
            "forward_return_mean": [metrics["forward_return_mean"]],
            "forward_return_median": [metrics["forward_return_median"]],
            "hit_rate": [metrics["hit_rate"]],
            "mfe_mean": [metrics["mfe_mean"]],
            "mfe_median": [metrics["mfe_median"]],
            "mae_mean": [metrics["mae_mean"]],
            "mae_median": [metrics["mae_median"]],
        },
        schema=empty_run_summaries().schema,
    )
    validate_run_summaries(summary)
    return summary


def summarize_run_summaries(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    min_sample_size: int,
    outcome_filter: OutcomeAnalyticsFilter,
) -> pl.DataFrame:
    """Return RunSummary rows for each requested horizon."""
    if not horizons:
        empty = empty_run_summaries()
        validate_run_summaries(empty)
        return empty

    summaries = [
        compute_run_summary(
            frame,
            horizon_bars=horizon,
            min_sample_size=min_sample_size,
            outcome_filter=outcome_filter,
        )
        for horizon in horizons
    ]
    combined = pl.concat(summaries)
    validate_run_summaries(combined)
    return combined
