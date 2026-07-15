"""Analyze one persisted Signal Research run — read-only analytics orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.diagnostics import compute_join_diagnostics
from trading_framework.research.analytics.dimensions import (
    AnalyticsTimestampBasis,
    GroupDimension,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.analytics.histograms import summarize_metric_histograms
from trading_framework.research.analytics.metadata import (
    DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE,
    AnalyticsResultMetadata,
    build_analytics_result_metadata,
)
from trading_framework.research.analytics.quality_flags import (
    SignalResearchQualityWarning,
    compute_signal_research_quality_warnings,
)
from trading_framework.research.analytics.summarize import summarize_analysis_frame
from trading_framework.research.datasets.signal_research import (
    RunDatasetRef,
    SignalResearchDatasetRepository,
)
from trading_framework.research.signal_research.definition import SignalResearchQualityRules


class AnalyzeSignalResearchError(ValidationError):
    """Raised when Signal Research analytics orchestration fails."""


@dataclass(frozen=True, slots=True)
class AnalyzeSignalResearchRequest:
    """Input for read-only analytics over one persisted Signal Research run."""

    run_ref: RunDatasetRef
    storage_root: Path
    horizons: tuple[int, ...] | None = None
    outcome_filter: OutcomeAnalyticsFilter = field(
        default_factory=OutcomeAnalyticsFilter.complete_only
    )
    group_by: tuple[GroupDimension, ...] = ()
    conditional_context: bool = False
    timestamp_basis: AnalyticsTimestampBasis = AnalyticsTimestampBasis.AVAILABLE_AT
    min_sample_size: int = 1
    interpretation_min_sample_size: int = DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE
    quality_rules: SignalResearchQualityRules | None = None

    def __post_init__(self) -> None:
        if self.min_sample_size < 1:
            msg = "min_sample_size must be at least 1"
            raise AnalyzeSignalResearchError(msg)
        if self.interpretation_min_sample_size < 1:
            msg = "interpretation_min_sample_size must be at least 1"
            raise AnalyzeSignalResearchError(msg)


@dataclass(frozen=True, slots=True)
class AnalyzeSignalResearchResult:
    """Ephemeral analytics result for one persisted run."""

    source_run_id: str
    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None
    distribution_summaries: pl.DataFrame
    join_diagnostics: pl.DataFrame
    metadata: AnalyticsResultMetadata
    quality_warnings: tuple[SignalResearchQualityWarning, ...] = ()
    metric_histograms: pl.DataFrame | None = None


def analyze_signal_research_run(
    request: AnalyzeSignalResearchRequest,
    *,
    repository: SignalResearchDatasetRepository | None = None,
) -> AnalyzeSignalResearchResult:
    """Load one persisted run and return read-only analytics summaries."""
    repo = repository or SignalResearchDatasetRepository(request.storage_root)
    envelope = repo.read(request.run_ref)
    frame = build_analysis_frame(envelope)

    horizons = request.horizons
    if horizons is None:
        horizons = envelope.manifest.horizon_bars_requested

    scope = envelope.manifest.effective_scope()
    summarized = summarize_analysis_frame(
        frame,
        horizons=horizons,
        outcome_filter=request.outcome_filter,
        min_sample_size=request.min_sample_size,
        interpretation_min_sample_size=request.interpretation_min_sample_size,
        research_scope=scope,
        group_by=request.group_by,
        conditional_context=request.conditional_context,
        timestamp_basis=request.timestamp_basis,
    )
    join_diagnostics = compute_join_diagnostics(
        envelope,
        frame,
        horizons=horizons,
        outcome_filter=request.outcome_filter,
        evaluation_timeframe=envelope.manifest.evaluation_timeframe,
    )

    metadata = build_analytics_result_metadata(
        manifest=envelope.manifest,
        timestamp_basis=request.timestamp_basis,
        outcome_filter=request.outcome_filter,
        min_sample_size=request.min_sample_size,
        interpretation_min_sample_size=request.interpretation_min_sample_size,
    )

    quality_warnings = compute_signal_research_quality_warnings(
        run_summaries=summarized.run_summaries,
        grouped_summaries=summarized.grouped_summaries,
        conditional_comparison=summarized.conditional_comparison,
        frame=frame,
        research_scope=scope,
        rules=request.quality_rules,
        outcome_filter=request.outcome_filter,
    )
    metric_histograms = summarize_metric_histograms(
        frame,
        horizons=horizons,
        outcome_filter=request.outcome_filter,
    )

    return AnalyzeSignalResearchResult(
        source_run_id=envelope.manifest.run_id,
        run_summaries=summarized.run_summaries,
        grouped_summaries=summarized.grouped_summaries,
        conditional_comparison=summarized.conditional_comparison,
        distribution_summaries=summarized.distribution_summaries,
        join_diagnostics=join_diagnostics,
        metadata=metadata,
        quality_warnings=quality_warnings,
        metric_histograms=metric_histograms,
    )
