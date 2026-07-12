"""Tests for Signal Research RunSummary aggregates."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.research.analytics.aggregates import (
    compute_run_summary,
    summarize_analysis_frame,
    summarize_run_summaries,
)
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.analytics.schemas import validate_run_summaries
from trading_framework.research.context.context_fact import empty_context_facts_dataframe
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations import empty_market_model_observations_dataframe
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.strategy.reference_price import ReferencePricePolicy


def _manifest() -> SignalResearchRunManifest:
    return SignalResearchRunManifest(
        run_id="summary-run",
        schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
        evaluation_timeframe="1m",
        signal_model_ids=("higher_low_long",),
        horizon_bars_requested=(5, 10),
        reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
        outcome_definition_fingerprint=outcome_definition_fingerprint((5, 10)),
    )


def _envelope(*, outcomes: pl.DataFrame, occurrences: pl.DataFrame) -> SignalResearchRunEnvelope:
    return SignalResearchRunEnvelope(
        manifest=_manifest(),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=outcomes,
        context=empty_context_facts_dataframe(),
    )


def _occurrences(*rows: str) -> pl.DataFrame:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return pl.DataFrame(
        {
            "occurrence_id": list(rows),
            "signal_model_id": ["higher_low_long"] * len(rows),
            "detected_at": [detected_at] * len(rows),
            "available_at": [detected_at] * len(rows),
            "direction": ["long"] * len(rows),
            "reference_price": [100.0] * len(rows),
            "instrument": ["TEST"] * len(rows),
            "evaluation_timeframe": ["1m"] * len(rows),
            "source_dataset_ref": ["test@1"] * len(rows),
        }
    )


def test_compute_run_summary_complete_only_metrics() -> None:
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1", "occ-2", "occ-3"],
            "horizon_bars": [5, 5, 5],
            "outcome_status": [
                OutcomeStatus.COMPLETE.value,
                OutcomeStatus.COMPLETE.value,
                OutcomeStatus.INCOMPLETE_HORIZON.value,
            ],
            "terminal_price": [101.0, 99.0, 100.0],
            "forward_return": [0.01, -0.01, 0.0],
            "mfe": [0.02, 0.01, 0.0],
            "mae": [-0.005, -0.02, 0.0],
        }
    )
    envelope = _envelope(
        outcomes=outcomes,
        occurrences=_occurrences("occ-1", "occ-2", "occ-3"),
    )
    frame = build_analysis_frame(envelope)

    summary = compute_run_summary(frame, horizon_bars=5, min_sample_size=1).row(0, named=True)

    assert summary["sample_size_total"] == 3
    assert summary["sample_size_complete"] == 2
    assert summary["sample_size_incomplete"] == 1
    assert summary["hit_rate"] == pytest.approx(0.5)
    assert summary["forward_return_mean"] == pytest.approx(0.0)


def test_compute_run_summary_metrics_eligible_false_keeps_row() -> None:
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "horizon_bars": [5],
            "outcome_status": [OutcomeStatus.COMPLETE.value],
            "terminal_price": [101.0],
            "forward_return": [0.01],
            "mfe": [0.02],
            "mae": [-0.005],
        }
    )
    frame = build_analysis_frame(_envelope(outcomes=outcomes, occurrences=_occurrences("occ-1")))

    summary = compute_run_summary(frame, horizon_bars=5, min_sample_size=10).row(0, named=True)

    assert summary["metrics_eligible"] is False
    assert summary["forward_return_mean"] is None
    assert summary["sample_size_complete"] == 1


def test_summarize_run_summaries_returns_one_row_per_horizon() -> None:
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1", "occ-1"],
            "horizon_bars": [5, 10],
            "outcome_status": [OutcomeStatus.COMPLETE.value, OutcomeStatus.COMPLETE.value],
            "terminal_price": [101.0, 102.0],
            "forward_return": [0.01, 0.02],
            "mfe": [0.02, 0.03],
            "mae": [-0.005, -0.01],
        }
    )
    frame = build_analysis_frame(_envelope(outcomes=outcomes, occurrences=_occurrences("occ-1")))

    summaries = summarize_run_summaries(
        frame,
        horizons=(5, 10),
        min_sample_size=1,
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
    )

    assert summaries.height == 2
    validate_run_summaries(summaries)


def test_summarize_analysis_frame_defers_grouping_and_conditional() -> None:
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "horizon_bars": [5],
            "outcome_status": [OutcomeStatus.COMPLETE.value],
            "terminal_price": [101.0],
            "forward_return": [0.01],
            "mfe": [0.02],
            "mae": [-0.005],
        }
    )
    frame = build_analysis_frame(_envelope(outcomes=outcomes, occurrences=_occurrences("occ-1")))

    result = summarize_analysis_frame(
        frame,
        horizons=(5,),
        min_sample_size=1,
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
    )

    assert result.run_summaries.height == 1
    assert result.grouped_summaries is None
    assert result.conditional_comparison is None
