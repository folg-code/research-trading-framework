"""Conditional context comparison for MARKET_AND_SIGNAL analytics."""

from __future__ import annotations

from enum import StrEnum

import polars as pl

from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metrics import aggregate_complete_metrics
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    validate_conditional_comparison,
)
from trading_framework.research.scope import ResearchScope


class ConditionalComparisonStatus(StrEnum):
    """Availability of a true-vs-false context comparison."""

    AVAILABLE = "available"
    EMPTY_CONDITIONED_SAMPLE = "empty_conditioned_sample"
    EMPTY_CONTROL_SAMPLE = "empty_control_sample"
    NO_COMPLETE_OUTCOMES = "no_complete_outcomes"


def _delta(true_val: float | None, false_val: float | None) -> float | None:
    if true_val is None or false_val is None:
        return None
    return true_val - false_val


def _resolve_status(
    *,
    true_count: int,
    false_count: int,
    missing_count: int,
) -> tuple[ConditionalComparisonStatus, str]:
    if true_count == 0 and false_count == 0 and missing_count == 0:
        return (
            ConditionalComparisonStatus.NO_COMPLETE_OUTCOMES,
            "No complete outcomes available for conditional comparison.",
        )
    if true_count == 0:
        reason = (
            "No complete outcomes matched context_met_at_available_at=true. "
            "Run-level metrics describe the signal baseline only; "
            "the MARKET_AND_SIGNAL hypothesis was not evaluated on a non-empty "
            "conditioned sample."
        )
        if missing_count > 0:
            reason += f" {missing_count} complete outcome(s) had unresolved context."
        return ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE, reason
    if false_count == 0:
        return (
            ConditionalComparisonStatus.EMPTY_CONTROL_SAMPLE,
            "No complete outcomes matched context_met_at_available_at=false.",
        )
    if missing_count > 0:
        return (
            ConditionalComparisonStatus.AVAILABLE,
            (
                f"Comparison uses explicit true/false context only. "
                f"{missing_count} complete outcome(s) had unresolved context and "
                "were excluded from both arms."
            ),
        )
    return ConditionalComparisonStatus.AVAILABLE, "Both context arms have complete outcomes."


def compute_conditional_comparison(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    outcome_filter: OutcomeAnalyticsFilter | None = None,
) -> pl.DataFrame:
    """Compare complete outcomes where context_met is true vs false.

    Unresolved context (``null``) is excluded from both arms and counted separately.
    """
    aggregate_filter = outcome_filter or OutcomeAnalyticsFilter.complete_only()
    subset = frame.filter(pl.col("horizon_bars") == horizon_bars)
    complete = aggregate_filter.filter_for_aggregates(subset)
    true_rows = complete.filter(pl.col("context_met_at_available_at").eq(True))
    false_rows = complete.filter(pl.col("context_met_at_available_at").eq(False))
    missing_rows = complete.filter(pl.col("context_met_at_available_at").is_null())

    true_metrics = aggregate_complete_metrics(true_rows)
    false_metrics = aggregate_complete_metrics(false_rows)
    status, reason = _resolve_status(
        true_count=len(true_rows),
        false_count=len(false_rows),
        missing_count=len(missing_rows),
    )

    run_id = str(subset.row(0, named=True)["run_id"]) if len(subset) else ""
    comparison = pl.DataFrame(
        {
            "run_id": [run_id],
            "horizon_bars": [horizon_bars],
            "context_true_sample_size": [len(true_rows)],
            "context_false_sample_size": [len(false_rows)],
            "context_missing_sample_size": [len(missing_rows)],
            "comparison_status": [status.value],
            "status_reason": [reason],
            "forward_return_mean_true": [true_metrics["forward_return_mean"]],
            "forward_return_mean_false": [false_metrics["forward_return_mean"]],
            "forward_return_mean_delta": [
                _delta(true_metrics["forward_return_mean"], false_metrics["forward_return_mean"])
            ],
            "hit_rate_true": [true_metrics["hit_rate"]],
            "hit_rate_false": [false_metrics["hit_rate"]],
            "hit_rate_delta": [_delta(true_metrics["hit_rate"], false_metrics["hit_rate"])],
            "mfe_mean_true": [true_metrics["mfe_mean"]],
            "mfe_mean_false": [false_metrics["mfe_mean"]],
            "mfe_mean_delta": [_delta(true_metrics["mfe_mean"], false_metrics["mfe_mean"])],
            "mae_mean_true": [true_metrics["mae_mean"]],
            "mae_mean_false": [false_metrics["mae_mean"]],
            "mae_mean_delta": [_delta(true_metrics["mae_mean"], false_metrics["mae_mean"])],
        },
        schema=empty_conditional_comparison().schema,
    )
    validate_conditional_comparison(comparison)
    return comparison


def summarize_conditional_comparison(
    frame: pl.DataFrame,
    *,
    horizons: tuple[int, ...],
    research_scope: ResearchScope,
    conditional_context: bool,
    outcome_filter: OutcomeAnalyticsFilter,
) -> pl.DataFrame | None:
    """Return conditional comparison rows when requested for MARKET_AND_SIGNAL."""
    if not conditional_context:
        return None
    if research_scope is not ResearchScope.MARKET_AND_SIGNAL:
        return None

    if not horizons:
        empty = empty_conditional_comparison()
        validate_conditional_comparison(empty)
        return empty

    parts = [
        compute_conditional_comparison(
            frame,
            horizon_bars=horizon,
            outcome_filter=outcome_filter,
        )
        for horizon in horizons
    ]
    combined = pl.concat(parts)
    validate_conditional_comparison(combined)
    return combined
