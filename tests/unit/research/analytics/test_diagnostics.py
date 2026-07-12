"""Tests for join diagnostics analytics."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from trading_framework.research.analytics.diagnostics import compute_join_diagnostics
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.frame_builder import build_analysis_frame
from trading_framework.research.datasets.signal_research import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations.market_model_observation import (
    empty_market_model_observations_dataframe,
)
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy


def _combined_envelope(*, context_values: list[bool | None]) -> SignalResearchRunEnvelope:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    available_at = datetime(2024, 1, 1, 12, 1, tzinfo=UTC)
    occurrences = pl.DataFrame(
        {
            "occurrence_id": [f"occ-{index}" for index in range(len(context_values))],
            "signal_model_id": ["signal"] * len(context_values),
            "detected_at": [detected_at] * len(context_values),
            "available_at": [available_at] * len(context_values),
            "direction": ["long"] * len(context_values),
            "reference_price": [100.0] * len(context_values),
            "instrument": ["TEST"] * len(context_values),
            "evaluation_timeframe": ["1m"] * len(context_values),
            "source_dataset_ref": ["test@1"] * len(context_values),
        }
    )
    context_rows = [
        {
            "occurrence_id": f"occ-{index}",
            "market_model_id": "market",
            "context_met_at_available_at": value,
            "context_evaluated_at": available_at,
        }
        for index, value in enumerate(context_values)
        if value is not None
    ]
    context = (
        pl.DataFrame(context_rows)
        if context_rows
        else pl.DataFrame(
            schema={
                "occurrence_id": pl.String(),
                "market_model_id": pl.String(),
                "context_met_at_available_at": pl.Boolean(),
                "context_evaluated_at": pl.Datetime(time_unit="us", time_zone="UTC"),
            }
        )
    )
    outcomes = pl.DataFrame(
        {
            "occurrence_id": [f"occ-{index}" for index in range(len(context_values))],
            "horizon_bars": [5] * len(context_values),
            "outcome_status": [OutcomeStatus.COMPLETE.value] * len(context_values),
            "terminal_price": [101.0] * len(context_values),
            "forward_return": [0.001] * len(context_values),
            "mfe": [0.002] * len(context_values),
            "mae": [-0.001] * len(context_values),
        }
    )
    manifest = SignalResearchRunManifest(
        run_id="run-1",
        schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
        framework_version="test",
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="dataset@1",
        evaluation_timeframe="1m",
        signal_model_ids=("signal",),
        horizon_bars_requested=(5,),
        reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
        outcome_definition_fingerprint=outcome_definition_fingerprint((5,)),
        research_scope=ResearchScope.MARKET_AND_SIGNAL,
        market_model_ids=("market",),
    )
    return SignalResearchRunEnvelope(
        manifest=manifest,
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=outcomes,
        context=context,
    )


def test_join_diagnostics_counts_missing_context_separately() -> None:
    envelope = _combined_envelope(context_values=[False, None])
    frame = build_analysis_frame(envelope)
    diagnostics = compute_join_diagnostics(
        envelope,
        frame,
        horizons=(5,),
        outcome_filter=OutcomeAnalyticsFilter.complete_only(),
        evaluation_timeframe="1m",
    ).row(0, named=True)

    assert diagnostics["entity_count"] == 2
    assert diagnostics["missing_context_rows"] == 1
    assert diagnostics["context_false_complete"] == 1
    assert diagnostics["context_missing_complete"] == 1
    assert diagnostics["context_true_complete"] == 0
