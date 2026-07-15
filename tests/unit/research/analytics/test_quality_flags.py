"""Unit tests for Signal Research quality diagnostic flags."""

from __future__ import annotations

import polars as pl

from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import GroupDimension
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.quality_flags import (
    SignalResearchQualityFlag,
    compute_signal_research_quality_warnings,
)
from trading_framework.research.analytics.schemas import (
    empty_analysis_frame,
    empty_conditional_comparison,
    empty_grouped_summaries,
    empty_run_summaries,
)
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import SignalResearchQualityRules


def _run_summary(
    *,
    horizon: int = 5,
    complete: int = 50,
    incomplete: int = 0,
) -> pl.DataFrame:
    total = complete + incomplete
    return pl.DataFrame(
        {
            "run_id": ["run-1"],
            "research_scope": [ResearchScope.SIGNAL_MODEL_ONLY.value],
            "horizon_bars": [horizon],
            "sample_size_total": [total],
            "sample_size_complete": [complete],
            "sample_size_incomplete": [incomplete],
            "completion_rate": [complete / total if total else 0.0],
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


def test_low_sample_size_flag() -> None:
    warnings = compute_signal_research_quality_warnings(
        run_summaries=_run_summary(complete=20),
        grouped_summaries=None,
        conditional_comparison=None,
        frame=empty_analysis_frame(),
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        rules=SignalResearchQualityRules(minimum_sample_size=100),
    )
    codes = {warning.code for warning in warnings}
    assert SignalResearchQualityFlag.LOW_SAMPLE_SIZE in codes


def test_incomplete_outcomes_flag() -> None:
    warnings = compute_signal_research_quality_warnings(
        run_summaries=_run_summary(complete=90, incomplete=10),
        grouped_summaries=None,
        conditional_comparison=None,
        frame=empty_analysis_frame(),
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        rules=SignalResearchQualityRules(maximum_incomplete_outcome_share=0.05),
    )
    codes = {warning.code for warning in warnings}
    assert SignalResearchQualityFlag.INCOMPLETE_OUTCOMES in codes


def test_high_period_concentration_flag() -> None:
    grouped = pl.DataFrame(
        {
            "run_id": ["run-1", "run-1"],
            "research_scope": [
                ResearchScope.SIGNAL_MODEL_ONLY.value,
                ResearchScope.SIGNAL_MODEL_ONLY.value,
            ],
            "horizon_bars": [5, 5],
            "group_dimension": [
                GroupDimension.CALENDAR_MONTH.value,
                GroupDimension.CALENDAR_MONTH.value,
            ],
            "group_value": ["2025-01", "2025-02"],
            "sample_size_total": [80, 20],
            "sample_size_complete": [80, 20],
            "sample_size_incomplete": [0, 0],
            "metrics_eligible": [True, True],
            "forward_return_mean": [0.0001, 0.0002],
            "forward_return_median": [0.0001, 0.0002],
            "hit_rate": [0.6, 0.6],
            "mfe_mean": [0.0002, 0.0002],
            "mfe_median": [0.0002, 0.0002],
            "mae_mean": [-0.0001, -0.0001],
            "mae_median": [-0.0001, -0.0001],
        },
        schema=empty_grouped_summaries().schema,
    )
    warnings = compute_signal_research_quality_warnings(
        run_summaries=_run_summary(complete=100),
        grouped_summaries=grouped,
        conditional_comparison=None,
        frame=empty_analysis_frame(),
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        rules=SignalResearchQualityRules(maximum_single_period_contribution=0.40),
    )
    codes = {warning.code for warning in warnings}
    assert SignalResearchQualityFlag.HIGH_PERIOD_CONCENTRATION in codes


def test_high_sample_loss_and_weak_baseline_flags() -> None:
    conditional = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "horizon_bars": [5],
            "context_true_sample_size": [5],
            "context_false_sample_size": [45],
            "context_missing_sample_size": [0],
            "comparison_status": [ConditionalComparisonStatus.AVAILABLE.value],
            "status_reason": ["Both context arms have complete outcomes."],
            "forward_return_mean_true": [0.0001],
            "forward_return_mean_false": [0.0002],
            "forward_return_mean_delta": [-0.0001],
            "hit_rate_true": [0.4],
            "hit_rate_false": [0.6],
            "hit_rate_delta": [-0.2],
            "mfe_mean_true": [0.0001],
            "mfe_mean_false": [0.0002],
            "mfe_mean_delta": [-0.0001],
            "mae_mean_true": [-0.0001],
            "mae_mean_false": [-0.0001],
            "mae_mean_delta": [0.0],
        },
        schema=empty_conditional_comparison().schema,
    )
    warnings = compute_signal_research_quality_warnings(
        run_summaries=_run_summary(complete=50),
        grouped_summaries=None,
        conditional_comparison=conditional,
        frame=empty_analysis_frame(),
        research_scope=ResearchScope.MARKET_AND_SIGNAL,
    )
    codes = {warning.code for warning in warnings}
    assert SignalResearchQualityFlag.HIGH_SAMPLE_LOSS in codes
    assert SignalResearchQualityFlag.WEAK_BASELINE_IMPROVEMENT in codes


def test_outlier_dependent_flag() -> None:
    frame = pl.DataFrame(
        {
            "run_id": ["run-1"] * 12,
            "research_scope": [ResearchScope.SIGNAL_MODEL_ONLY.value] * 12,
            "entity_id": [f"e-{index}" for index in range(12)],
            "entity_kind": ["SIGNAL_OCCURRENCE"] * 12,
            "horizon_bars": [5] * 12,
            "outcome_status": [OutcomeStatus.COMPLETE.value] * 12,
            "forward_return": [-0.0001] * 11 + [0.05],
            "mfe": [0.0002] * 12,
            "mae": [-0.0001] * 12,
            "detected_at": [None] * 12,
            "available_at": [None] * 12,
            "reference_price": [100.0] * 12,
            "instrument": ["TEST"] * 12,
            "context_met_at_available_at": [None] * 12,
        },
        schema=empty_analysis_frame().schema,
    )
    warnings = compute_signal_research_quality_warnings(
        run_summaries=_run_summary(complete=12),
        grouped_summaries=None,
        conditional_comparison=None,
        frame=frame,
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY,
        rules=SignalResearchQualityRules(minimum_sample_size=1),
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
    )
    codes = {warning.code for warning in warnings}
    assert SignalResearchQualityFlag.OUTLIER_DEPENDENT in codes
