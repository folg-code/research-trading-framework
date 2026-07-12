"""Tests for scope-aware Signal Research analysis frame builder."""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.research.analytics import (
    ENTITY_KIND_OBSERVATION,
    ENTITY_KIND_SIGNAL,
    build_analysis_frame,
    validate_analysis_frame,
)
from trading_framework.research.context.context_fact import empty_context_facts_dataframe
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_V2,
    SIGNAL_RESEARCH_SCHEMA_VERSION,
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


def _manifest(*, scope: ResearchScope | None = None) -> SignalResearchRunManifest:
    if scope is None:
        return SignalResearchRunManifest(
            run_id="signal-run",
            schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
            framework_version=framework_version,
            created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
            source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
            evaluation_timeframe="1m",
            signal_model_ids=("higher_low_long",),
            horizon_bars_requested=(5,),
            reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            outcome_definition_fingerprint=outcome_definition_fingerprint((5,)),
        )
    signal_model_ids: tuple[str, ...] = ()
    market_model_ids: tuple[str, ...] = ()
    if scope is not ResearchScope.MARKET_MODEL_ONLY:
        signal_model_ids = ("higher_low_long",)
    if scope is not ResearchScope.SIGNAL_MODEL_ONLY:
        market_model_ids = ("high_volatility",)
    return SignalResearchRunManifest(
        run_id=f"{scope.value}-run",
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


def _outcome_row(*, entity_id: str) -> dict[str, object]:
    return {
        "occurrence_id": entity_id,
        "horizon_bars": 5,
        "outcome_status": OutcomeStatus.COMPLETE.value,
        "terminal_price": 101.0,
        "forward_return": 0.01,
        "mfe": 0.02,
        "mae": -0.005,
    }


def test_build_analysis_frame_signal_model_only_v1() -> None:
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
        manifest=_manifest(),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=pl.DataFrame([_outcome_row(entity_id="occ-1")]),
        context=empty_context_facts_dataframe(),
    )

    frame = build_analysis_frame(envelope)

    assert frame.height == 1
    assert frame.row(0, named=True)["entity_id"] == "occ-1"
    assert frame.row(0, named=True)["entity_kind"] == ENTITY_KIND_SIGNAL
    assert frame.row(0, named=True)["context_met_at_available_at"] is None
    validate_analysis_frame(frame)


def test_build_analysis_frame_market_model_only_uses_observation_id() -> None:
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
    envelope = SignalResearchRunEnvelope(
        manifest=_manifest(scope=ResearchScope.MARKET_MODEL_ONLY),
        occurrences=empty_signal_occurrences_dataframe(),
        observations=observations,
        outcomes=pl.DataFrame([_outcome_row(entity_id="obs-1")]),
        context=empty_context_facts_dataframe(),
    )

    frame = build_analysis_frame(envelope)

    assert frame.row(0, named=True)["entity_id"] == "obs-1"
    assert frame.row(0, named=True)["entity_kind"] == ENTITY_KIND_OBSERVATION
    assert frame.row(0, named=True)["research_scope"] == ResearchScope.MARKET_MODEL_ONLY.value


def test_build_analysis_frame_market_and_signal_includes_context() -> None:
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
            "context_met_at_available_at": [True],
            "context_evaluated_at": [available_at],
        }
    )
    envelope = SignalResearchRunEnvelope(
        manifest=_manifest(scope=ResearchScope.MARKET_AND_SIGNAL),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=pl.DataFrame([_outcome_row(entity_id="occ-1")]),
        context=context,
    )

    frame = build_analysis_frame(envelope)

    assert frame.row(0, named=True)["context_met_at_available_at"] is True


def test_build_analysis_frame_empty_outcomes_returns_valid_schema() -> None:
    envelope = SignalResearchRunEnvelope(
        manifest=_manifest(),
        occurrences=empty_signal_occurrences_dataframe(),
        observations=empty_market_model_observations_dataframe(),
        outcomes=empty_forward_outcomes_dataframe(),
        context=empty_context_facts_dataframe(),
    )

    frame = build_analysis_frame(envelope)

    assert frame.is_empty()
    validate_analysis_frame(frame)
