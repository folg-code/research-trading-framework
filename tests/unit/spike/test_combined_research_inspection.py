"""Tests for combined research inspection helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pytest

from tests.spike._combined_research_inspection import build_combined_inspection_selection
from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.context.context_fact import empty_context_facts_dataframe
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations import empty_market_model_observations_dataframe
from trading_framework.research.outcomes.calculator import empty_forward_outcomes_dataframe
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe


def _v2_manifest(*, scope: ResearchScope) -> SignalResearchRunManifest:
    signal_model_ids: tuple[str, ...] = ()
    market_model_ids: tuple[str, ...] = ()
    if scope is not ResearchScope.MARKET_MODEL_ONLY:
        signal_model_ids = ("higher_low_long",)
    if scope is not ResearchScope.SIGNAL_MODEL_ONLY:
        market_model_ids = ("high_volatility",)
    return SignalResearchRunManifest(
        run_id="inspect-run",
        schema_version=SIGNAL_RESEARCH_SCHEMA_V2,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
        evaluation_timeframe="1m",
        signal_model_ids=signal_model_ids,
        horizon_bars_requested=(5,),
        reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
        outcome_definition_fingerprint=outcome_definition_fingerprint((5,)),
        research_scope=scope,
        market_model_ids=market_model_ids,
    )


def test_build_combined_inspection_selection_market_and_signal_includes_context() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    available_at = datetime(2024, 1, 1, 12, 1, tzinfo=UTC)
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "signal_model_id": ["higher_low_long"],
            "detected_at": [detected_at],
            "available_at": [available_at],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test@1"],
        }
    )
    context = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "market_model_id": ["high_volatility"],
            "context_met_at_available_at": [False],
            "context_evaluated_at": [available_at],
        }
    )
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "horizon_bars": [5],
            "outcome_status": [OutcomeStatus.COMPLETE.value],
            "terminal_price": [102.0],
            "forward_return": [0.02],
            "mfe": [0.03],
            "mae": [-0.01],
        }
    )
    envelope = SignalResearchRunEnvelope(
        manifest=_v2_manifest(scope=ResearchScope.MARKET_AND_SIGNAL),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=outcomes,
        context=context,
    )

    combined = build_combined_inspection_selection(
        envelope,
        horizon_bars=5,
        fact_index=0,
    )

    assert combined.scope is ResearchScope.MARKET_AND_SIGNAL
    assert combined.context_met_at_available_at is False
    assert combined.selection.mfe == pytest.approx(0.03)
    assert combined.selection.mae == pytest.approx(-0.01)
    assert combined.selection.forward_return == pytest.approx(0.02)


def test_build_combined_inspection_selection_market_only_uses_observation_id() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    observations = pl.DataFrame(
        {
            "observation_id": ["obs-1"],
            "market_model_id": ["high_volatility"],
            "detected_at": [detected_at],
            "available_at": [detected_at],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test@1"],
        }
    )
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["obs-1"],
            "horizon_bars": [5],
            "outcome_status": [OutcomeStatus.COMPLETE.value],
            "terminal_price": [101.0],
            "forward_return": [0.01],
            "mfe": [0.02],
            "mae": [-0.005],
        }
    )
    envelope = SignalResearchRunEnvelope(
        manifest=_v2_manifest(scope=ResearchScope.MARKET_MODEL_ONLY),
        occurrences=empty_signal_occurrences_dataframe(),
        observations=observations,
        outcomes=outcomes,
        context=empty_context_facts_dataframe(),
    )

    combined = build_combined_inspection_selection(
        envelope,
        horizon_bars=5,
        fact_index=0,
    )

    assert combined.fact_kind == "observation"
    assert combined.fact_id == "obs-1"
    assert combined.selection.terminal_price == pytest.approx(101.0)


def test_build_combined_inspection_selection_requires_context_row() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "signal_model_id": ["higher_low_long"],
            "detected_at": [detected_at],
            "available_at": [detected_at],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test@1"],
        }
    )
    envelope = SignalResearchRunEnvelope(
        manifest=_v2_manifest(scope=ResearchScope.MARKET_AND_SIGNAL),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=empty_forward_outcomes_dataframe(),
        context=empty_context_facts_dataframe(),
    )

    with pytest.raises(ValidationError, match="context row missing"):
        build_combined_inspection_selection(envelope, horizon_bars=5, fact_index=0)
