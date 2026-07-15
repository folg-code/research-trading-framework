"""Tests for model-family comparison analytics."""

from __future__ import annotations

import polars as pl

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)
from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.family_comparison import summarize_family_comparison
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    empty_distribution_summaries,
    empty_join_diagnostics,
    empty_run_summaries,
    validate_family_comparison,
)
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy


def _analytics(*, variant_suffix: str, sample: int, mean: float) -> AnalyzeSignalResearchResult:
    run_summaries = pl.DataFrame(
        {
            "run_id": [f"run-{variant_suffix}"],
            "research_scope": [ResearchScope.SIGNAL_MODEL_ONLY.value],
            "horizon_bars": [5],
            "sample_size_total": [sample],
            "sample_size_complete": [sample],
            "sample_size_incomplete": [0],
            "completion_rate": [1.0],
            "minimum_required": [1],
            "metrics_eligible": [True],
            "forward_return_mean": [mean],
            "forward_return_median": [mean / 2],
            "hit_rate": [0.55],
            "mfe_mean": [0.0002],
            "mfe_median": [0.00015],
            "mae_mean": [-0.0001],
            "mae_median": [-0.00008],
        },
        schema=empty_run_summaries().schema,
    )
    return AnalyzeSignalResearchResult(
        source_run_id=f"run-{variant_suffix}",
        run_summaries=run_summaries,
        grouped_summaries=None,
        conditional_comparison=pl.DataFrame(
            {
                "run_id": ["run-x"],
                "horizon_bars": [5],
                "context_true_sample_size": [0],
                "context_false_sample_size": [0],
                "context_missing_sample_size": [0],
                "comparison_status": [ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE.value],
                "status_reason": ["n/a"],
                "forward_return_mean_true": [None],
                "forward_return_mean_false": [None],
                "forward_return_mean_delta": [None],
                "forward_return_median_true": [None],
                "forward_return_median_false": [None],
                "forward_return_median_delta": [None],
                "hit_rate_true": [None],
                "hit_rate_false": [None],
                "hit_rate_delta": [None],
                "mfe_mean_true": [None],
                "mfe_mean_false": [None],
                "mfe_mean_delta": [None],
                "mfe_median_true": [None],
                "mfe_median_false": [None],
                "mfe_median_delta": [None],
                "mae_mean_true": [None],
                "mae_mean_false": [None],
                "mae_mean_delta": [None],
                "mae_median_true": [None],
                "mae_median_false": [None],
                "mae_median_delta": [None],
            },
            schema=empty_conditional_comparison().schema,
        ),
        distribution_summaries=empty_distribution_summaries(),
        join_diagnostics=empty_join_diagnostics(),
        metadata=AnalyticsResultMetadata(
            source_run_id=f"run-{variant_suffix}",
            research_scope=ResearchScope.SIGNAL_MODEL_ONLY.value,
            timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
            outcome_filter=OutcomeAnalyticsFilter.complete_only(),
            evaluation_timeframe="1m",
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            market_model_ids=(),
            signal_model_ids=(f"signal_{variant_suffix}",),
            min_sample_size=1,
            interpretation_min_sample_size=30,
        ),
    )


def test_summarize_family_comparison_orders_variants() -> None:
    comparison = summarize_family_comparison(
        (
            ("higher_low", "run-a", _analytics(variant_suffix="a", sample=40, mean=0.0001)),
            ("vol_edge", "run-b", _analytics(variant_suffix="b", sample=20, mean=0.0002)),
        )
    )
    validate_family_comparison(comparison)
    rows = comparison.to_dicts()
    assert [row["variant_id"] for row in rows] == ["higher_low", "vol_edge"]
    assert rows[0]["sample_size_complete"] == 40
    assert rows[1]["forward_return_mean"] == 0.0002
