"""Tests for Signal Research analytics HTML reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.quality_flags import (
    SignalResearchQualityFlag,
    SignalResearchQualityWarning,
)
from trading_framework.research.analytics.reports import render_signal_research_report
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    empty_distribution_summaries,
    empty_join_diagnostics,
    empty_run_summaries,
)
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy


@dataclass(frozen=True, slots=True)
class _ReportFixtureResult:
    source_run_id: str
    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None
    distribution_summaries: pl.DataFrame
    join_diagnostics: pl.DataFrame
    metadata: AnalyticsResultMetadata
    quality_warnings: tuple[SignalResearchQualityWarning, ...] = ()


def _metadata(*, scope: str = ResearchScope.MARKET_AND_SIGNAL.value) -> AnalyticsResultMetadata:
    return AnalyticsResultMetadata(
        source_run_id="run-1",
        research_scope=scope,
        timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
        evaluation_timeframe="1m",
        reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
        market_model_ids=("high_volatility",),
        signal_model_ids=("higher_low_long",),
        min_sample_size=1,
        interpretation_min_sample_size=30,
    )


def _distribution_summaries(*, interpretable: bool = True) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "run_id": ["run-1"],
            "horizon_bars": [5],
            "sample_size_complete": [50],
            "minimum_required": [1],
            "interpretation_minimum_required": [30],
            "metrics_computable": [True],
            "metrics_interpretable": [interpretable],
            "forward_return_p10": [-0.0001],
            "forward_return_p25": [-0.00005],
            "forward_return_p75": [0.00015],
            "forward_return_p90": [0.0002],
            "forward_return_std": [0.00012],
            "forward_return_min": [-0.0002],
            "forward_return_max": [0.0003],
        },
        schema=empty_distribution_summaries().schema,
    )


def _join_diagnostics() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "run_id": ["run-1"],
            "horizon_bars": [5],
            "entity_count": [50],
            "outcome_rows_total": [50],
            "outcome_rows_complete": [50],
            "outcome_rows_unmatched_entity": [0],
            "matched_context_rows": [50],
            "missing_context_rows": [0],
            "duplicate_context_matches": [0],
            "context_true_complete": [10],
            "context_false_complete": [40],
            "context_missing_complete": [0],
            "overlapping_outcome_windows": [12],
            "overlapping_outcome_rate": [0.24],
        },
        schema=empty_join_diagnostics().schema,
    )


def _sample_result(*, include_conditional: bool) -> _ReportFixtureResult:
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
    conditional = None
    if include_conditional:
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
                "hit_rate_true": [0.7],
                "hit_rate_false": [0.55],
                "hit_rate_delta": [0.15],
                "mfe_mean_true": [0.0003],
                "mfe_mean_false": [0.00018],
                "mfe_mean_delta": [0.00012],
                "mae_mean_true": [-0.00008],
                "mae_mean_false": [-0.00011],
                "mae_mean_delta": [0.00003],
            },
            schema=empty_conditional_comparison().schema,
        )
    return _ReportFixtureResult(
        source_run_id="run-1",
        run_summaries=run_summaries,
        grouped_summaries=None,
        conditional_comparison=conditional,
        distribution_summaries=_distribution_summaries(),
        join_diagnostics=_join_diagnostics(),
        metadata=_metadata(),
    )


def test_render_signal_research_report_rejects_empty_summaries(tmp_path: Path) -> None:
    result = _ReportFixtureResult(
        source_run_id="run-1",
        run_summaries=empty_run_summaries(),
        grouped_summaries=None,
        conditional_comparison=None,
        distribution_summaries=empty_distribution_summaries(),
        join_diagnostics=empty_join_diagnostics(),
        metadata=_metadata(scope=ResearchScope.SIGNAL_MODEL_ONLY.value),
    )
    with pytest.raises(ValidationError, match="run_summaries must contain"):
        render_signal_research_report(result, tmp_path / "report.html")


def test_render_signal_research_report_writes_html(tmp_path: Path) -> None:
    plotly = pytest.importorskip("plotly")
    assert plotly is not None

    output = tmp_path / "report.html"
    result = _sample_result(include_conditional=True)
    result = _ReportFixtureResult(
        source_run_id=result.source_run_id,
        run_summaries=result.run_summaries,
        grouped_summaries=result.grouped_summaries,
        conditional_comparison=result.conditional_comparison,
        distribution_summaries=result.distribution_summaries,
        join_diagnostics=result.join_diagnostics,
        metadata=result.metadata,
        quality_warnings=(
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.LOW_SAMPLE_SIZE,
                message="Complete sample size 50 is below the configured minimum of 100.",
                horizon_bars=5,
            ),
        ),
    )
    path = render_signal_research_report(result, output)

    assert path == output
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "run-1" in content
    assert "Join diagnostics" in content
    assert "Signal baseline metrics" in content
    assert "Interpretation eligible" in content
    assert "Quality diagnostic flags" in content
    assert "LOW_SAMPLE_SIZE" in content
    assert "bps" in content
    assert "plotly" in content.lower()


def test_render_signal_research_report_warns_on_empty_conditioned_sample(tmp_path: Path) -> None:
    pytest.importorskip("plotly")
    result = _sample_result(include_conditional=True)
    conditional = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "horizon_bars": [5],
            "context_true_sample_size": [0],
            "context_false_sample_size": [50],
            "context_missing_sample_size": [0],
            "comparison_status": [ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE.value],
            "status_reason": ["No complete outcomes matched context_met_at_available_at=true."],
            "forward_return_mean_true": [None],
            "forward_return_mean_false": [0.0001],
            "forward_return_mean_delta": [None],
            "hit_rate_true": [None],
            "hit_rate_false": [0.6],
            "hit_rate_delta": [None],
            "mfe_mean_true": [None],
            "mfe_mean_false": [0.0002],
            "mfe_mean_delta": [None],
            "mae_mean_true": [None],
            "mae_mean_false": [-0.0001],
            "mae_mean_delta": [None],
        },
        schema=empty_conditional_comparison().schema,
    )
    result = _ReportFixtureResult(
        source_run_id=result.source_run_id,
        run_summaries=result.run_summaries,
        grouped_summaries=result.grouped_summaries,
        conditional_comparison=conditional,
        distribution_summaries=result.distribution_summaries,
        join_diagnostics=result.join_diagnostics,
        metadata=result.metadata,
    )
    output = tmp_path / "report.html"
    render_signal_research_report(result, output)
    content = output.read_text(encoding="utf-8")
    assert "Conditional comparison unavailable" in content
    assert "signal baseline" in content.lower()


def test_render_signal_research_report_includes_grouped_summaries(tmp_path: Path) -> None:
    pytest.importorskip("plotly")
    from trading_framework.research.analytics.schemas import empty_grouped_summaries

    result = _sample_result(include_conditional=False)
    grouped = pl.DataFrame(
        {
            "run_id": ["run-1"],
            "research_scope": [ResearchScope.MARKET_AND_SIGNAL.value],
            "horizon_bars": [5],
            "group_dimension": ["RTH_MEMBERSHIP"],
            "group_value": ["RTH"],
            "sample_size_total": [30],
            "sample_size_complete": [28],
            "sample_size_incomplete": [2],
            "metrics_eligible": [True],
            "forward_return_mean": [0.0002],
            "forward_return_median": [0.0001],
            "hit_rate": [0.55],
            "mfe_mean": [0.0003],
            "mfe_median": [0.0002],
            "mae_mean": [-0.00012],
            "mae_median": [-0.0001],
        },
        schema=empty_grouped_summaries().schema,
    )
    result = _ReportFixtureResult(
        source_run_id=result.source_run_id,
        run_summaries=result.run_summaries,
        grouped_summaries=grouped,
        conditional_comparison=result.conditional_comparison,
        distribution_summaries=result.distribution_summaries,
        join_diagnostics=result.join_diagnostics,
        metadata=result.metadata,
    )
    output = tmp_path / "report.html"
    render_signal_research_report(result, output)
    content = output.read_text(encoding="utf-8")
    assert "Grouped summaries" in content
    assert "signal-time session membership" in content
