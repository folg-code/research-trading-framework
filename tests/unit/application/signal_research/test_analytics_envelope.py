"""Tests for Signal Research analytics envelope serialization."""

from __future__ import annotations

import polars as pl

from trading_framework.application.signal_research.analytics_envelope import (
    signal_research_analytics_from_dict,
    signal_research_analytics_to_dict,
)
from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)
from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.quality_flags import (
    SignalResearchQualityFlag,
    SignalResearchQualityWarning,
)
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    empty_distribution_summaries,
    empty_join_diagnostics,
    empty_metric_histograms,
    empty_run_summaries,
)
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy


def _sample_result() -> AnalyzeSignalResearchResult:
    run_summaries = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "research_scope": [ResearchScope.MARKET_AND_SIGNAL.value],
            "horizon_bars": [5],
            "sample_size_total": [50],
            "sample_size_complete": [50],
            "sample_size_incomplete": [0],
            "completion_rate": [1.0],
            "minimum_required": [1],
            "metrics_eligible": [True],
            "forward_return_mean": [0.0001],
            "forward_return_median": [0.00005],
            "hit_rate": [0.6],
            "mfe_mean": [0.0002],
            "mfe_median": [0.00015],
            "mae_mean": [-0.0001],
            "mae_median": [-0.00008],
        },
        schema=empty_run_summaries().schema,
    )
    conditional = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "horizon_bars": [5],
            "context_true_sample_size": [10],
            "context_false_sample_size": [40],
            "context_missing_sample_size": [0],
            "comparison_status": [ConditionalComparisonStatus.AVAILABLE.value],
            "status_reason": ["Both context arms have complete outcomes."],
            "forward_return_mean_true": [0.0002],
            "forward_return_mean_false": [0.00005],
            "forward_return_mean_delta": [0.00015],
            "forward_return_median_true": [0.00018],
            "forward_return_median_false": [0.00004],
            "forward_return_median_delta": [0.00014],
            "hit_rate_true": [0.7],
            "hit_rate_false": [0.55],
            "hit_rate_delta": [0.15],
            "mfe_mean_true": [0.0003],
            "mfe_mean_false": [0.00018],
            "mfe_mean_delta": [0.00012],
            "mfe_median_true": [0.00025],
            "mfe_median_false": [0.00015],
            "mfe_median_delta": [0.0001],
            "mae_mean_true": [-0.00008],
            "mae_mean_false": [-0.00011],
            "mae_mean_delta": [0.00003],
            "mae_median_true": [-0.00007],
            "mae_median_false": [-0.0001],
            "mae_median_delta": [0.00003],
        },
        schema=empty_conditional_comparison().schema,
    )
    return AnalyzeSignalResearchResult(
        source_run_id="run-1",
        run_summaries=run_summaries,
        grouped_summaries=None,
        conditional_comparison=conditional,
        distribution_summaries=empty_distribution_summaries(),
        join_diagnostics=empty_join_diagnostics(),
        metadata=AnalyticsResultMetadata(
            source_run_id="run-1",
            research_scope=ResearchScope.MARKET_AND_SIGNAL.value,
            timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
            outcome_filter=OutcomeAnalyticsFilter.complete_only(),
            evaluation_timeframe="1m",
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            market_model_ids=("high_volatility",),
            signal_model_ids=("higher_low_long",),
            min_sample_size=1,
            interpretation_min_sample_size=30,
        ),
        quality_warnings=(
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.LOW_SAMPLE_SIZE,
                message="Complete sample size 50 is below the configured minimum of 100.",
                horizon_bars=5,
            ),
        ),
        metric_histograms=empty_metric_histograms(),
    )


def test_analytics_envelope_round_trip_preserves_summaries() -> None:
    original = _sample_result()
    restored = signal_research_analytics_from_dict(signal_research_analytics_to_dict(original))

    assert restored.source_run_id == original.source_run_id
    assert restored.run_summaries.equals(original.run_summaries)
    assert restored.conditional_comparison is not None
    assert original.conditional_comparison is not None
    assert restored.conditional_comparison.equals(original.conditional_comparison)
    assert len(restored.quality_warnings) == 1
    assert restored.quality_warnings[0].code is SignalResearchQualityFlag.LOW_SAMPLE_SIZE
