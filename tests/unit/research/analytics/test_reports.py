"""Tests for Signal Research analytics HTML reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.reports import render_signal_research_report
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    empty_run_summaries,
)
from trading_framework.research.scope import ResearchScope


@dataclass(frozen=True, slots=True)
class _ReportFixtureResult:
    source_run_id: str
    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None
    metadata: AnalyticsResultMetadata


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
    metadata = AnalyticsResultMetadata(
        source_run_id="run-1",
        research_scope=ResearchScope.MARKET_AND_SIGNAL.value,
        timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
    )
    return _ReportFixtureResult(
        source_run_id="run-1",
        run_summaries=run_summaries,
        grouped_summaries=None,
        conditional_comparison=conditional,
        metadata=metadata,
    )


def test_render_signal_research_report_rejects_empty_summaries(tmp_path: Path) -> None:
    metadata = AnalyticsResultMetadata(
        source_run_id="run-1",
        research_scope=ResearchScope.SIGNAL_MODEL_ONLY.value,
        timestamp_basis=AnalyticsTimestampBasis.AVAILABLE_AT,
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
    )
    result = _ReportFixtureResult(
        source_run_id="run-1",
        run_summaries=empty_run_summaries(),
        grouped_summaries=None,
        conditional_comparison=None,
        metadata=metadata,
    )
    with pytest.raises(ValidationError, match="run_summaries must contain"):
        render_signal_research_report(result, tmp_path / "report.html")


def test_render_signal_research_report_writes_html(tmp_path: Path) -> None:
    plotly = pytest.importorskip("plotly")
    assert plotly is not None

    output = tmp_path / "report.html"
    path = render_signal_research_report(_sample_result(include_conditional=True), output)

    assert path == output
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "run-1" in content
    assert "plotly" in content.lower()
