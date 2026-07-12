"""Orchestrate RunSummary, grouping and conditional analytics."""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from trading_framework.research.analytics.aggregates import summarize_run_summaries
from trading_framework.research.analytics.conditional import summarize_conditional_comparison
from trading_framework.research.analytics.dimensions import (
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.grouping import summarize_grouped_summaries
from trading_framework.research.scope import ResearchScope


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
    research_scope: ResearchScope,
    group_by: tuple[GroupDimension, ...] = (),
    conditional_context: bool = False,
    timestamp_basis: AnalyticsTimestampBasis = AnalyticsTimestampBasis.AVAILABLE_AT,
) -> SummarizeAnalysisFrameResult:
    """Compute RunSummary, optional grouping and conditional comparison."""
    run_summaries = summarize_run_summaries(
        frame,
        horizons=horizons,
        min_sample_size=min_sample_size,
        outcome_filter=outcome_filter,
    )
    grouped_summaries = summarize_grouped_summaries(
        frame,
        horizons=horizons,
        group_by=group_by,
        min_sample_size=min_sample_size,
        outcome_filter=outcome_filter,
        timestamp_basis=timestamp_basis,
    )
    conditional_comparison = summarize_conditional_comparison(
        frame,
        horizons=horizons,
        research_scope=research_scope,
        conditional_context=conditional_context,
        outcome_filter=outcome_filter,
    )
    return SummarizeAnalysisFrameResult(
        run_summaries=run_summaries,
        grouped_summaries=grouped_summaries,
        conditional_comparison=conditional_comparison,
    )
