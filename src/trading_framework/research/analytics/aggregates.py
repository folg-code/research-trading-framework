"""Run-level aggregate metrics for Signal Research analytics."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.schemas import (
    empty_run_summaries,
    validate_run_summaries,
)


def aggregate_complete_metrics(complete: pl.DataFrame) -> dict[str, float | None]:
    """Compute aggregate metrics over filter-eligible complete rows."""
    return _aggregate_complete_metrics(complete)


def _aggregate_complete_metrics(complete: pl.DataFrame) -> dict[str, float | None]:
    if len(complete) == 0:
        return {
            "forward_return_mean": None,
            "forward_return_median": None,
            "hit_rate": None,
            "mfe_mean": None,
            "mfe_median": None,
            "mae_mean": None,
            "mae_median": None,
        }
    returns = complete["forward_return"]
    hits = complete.filter(pl.col("forward_return") > 0).height
    return {
        "forward_return_mean": float(returns.mean()),  # type: ignore[arg-type]
        "forward_return_median": float(returns.median()),  # type: ignore[arg-type]
        "hit_rate": hits / len(complete),
        "mfe_mean": float(complete["mfe"].mean()),  # type: ignore[arg-type]
        "mfe_median": float(complete["mfe"].median()),  # type: ignore[arg-type]
        "mae_mean": float(complete["mae"].mean()),  # type: ignore[arg-type]
        "mae_median": float(complete["mae"].median()),  # type: ignore[arg-type]
    }


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
        metrics = _aggregate_complete_metrics(complete)
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


@dataclass(frozen=True, slots=True)
class SummarizeAnalysisFrameResult:
    """Ephemeral analytics outputs derived from one normalized analysis frame."""

    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None


def summarize_analysis_frame(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    outcome_filter: OutcomeAnalyticsFilter,
    min_sample_size: int,
) -> SummarizeAnalysisFrameResult:
    """Compute RunSummary aggregates for one analysis frame.

    Grouping and conditional comparison are populated in Wave 3.
    """
    run_summaries = summarize_run_summaries(
        frame,
        horizons=horizons,
        min_sample_size=min_sample_size,
        outcome_filter=outcome_filter,
    )
    return SummarizeAnalysisFrameResult(
        run_summaries=run_summaries,
        grouped_summaries=None,
        conditional_comparison=None,
    )
