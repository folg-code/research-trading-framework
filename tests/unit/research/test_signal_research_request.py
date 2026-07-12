"""Unit tests for SignalResearchRequest and scope validation."""

from __future__ import annotations

import pytest

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.research import (
    ForwardOutcomeDefinition,
    ResearchScope,
    SignalResearchRequest,
    SignalResearchRequestError,
    validate_signal_research_request,
)
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="test",
        ),
        version=1,
    )


def _outcome_definition() -> ForwardOutcomeDefinition:
    return ForwardOutcomeDefinition(horizon_bars=5)


def test_signal_only_factory_passes_validation() -> None:
    request = SignalResearchRequest.signal_only(
        dataset_ref=_dataset_ref(),
        signal_models=(build_canonical_signal_higher_low_on_event(),),
        outcome_definition=_outcome_definition(),
    )
    validate_signal_research_request(request)
    assert request.scope is ResearchScope.SIGNAL_MODEL_ONLY


def test_market_only_factory_passes_validation() -> None:
    request = SignalResearchRequest.market_only(
        dataset_ref=_dataset_ref(),
        market_models=(build_canonical_market_model_high_volatility(),),
        outcome_definition=_outcome_definition(),
    )
    validate_signal_research_request(request)
    assert request.scope is ResearchScope.MARKET_MODEL_ONLY


def test_market_and_signal_factory_passes_validation() -> None:
    request = SignalResearchRequest.market_and_signal(
        dataset_ref=_dataset_ref(),
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(build_canonical_signal_higher_low_on_event(),),
        outcome_definition=_outcome_definition(),
    )
    validate_signal_research_request(request)
    assert request.scope is ResearchScope.MARKET_AND_SIGNAL


def test_signal_only_rejects_market_models() -> None:
    request = SignalResearchRequest(
        scope=ResearchScope.SIGNAL_MODEL_ONLY,
        dataset_ref=_dataset_ref(),
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(build_canonical_signal_higher_low_on_event(),),
        outcome_definition=_outcome_definition(),
    )
    with pytest.raises(SignalResearchRequestError, match="rejects market_models"):
        validate_signal_research_request(request)


def test_market_only_rejects_signal_models() -> None:
    request = SignalResearchRequest(
        scope=ResearchScope.MARKET_MODEL_ONLY,
        dataset_ref=_dataset_ref(),
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(build_canonical_signal_higher_low_on_event(),),
        outcome_definition=_outcome_definition(),
    )
    with pytest.raises(SignalResearchRequestError, match="rejects signal_models"):
        validate_signal_research_request(request)


def test_market_and_signal_requires_both_models() -> None:
    request = SignalResearchRequest(
        scope=ResearchScope.MARKET_AND_SIGNAL,
        dataset_ref=_dataset_ref(),
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(),
        outcome_definition=_outcome_definition(),
    )
    with pytest.raises(SignalResearchRequestError, match="requires exactly one signal model"):
        validate_signal_research_request(request)


def test_rejects_duplicate_signal_model_ids() -> None:
    signal_model = build_canonical_signal_higher_low_on_event()
    request = SignalResearchRequest.signal_only(
        dataset_ref=_dataset_ref(),
        signal_models=(signal_model, signal_model),
        outcome_definition=_outcome_definition(),
    )
    with pytest.raises(SignalResearchRequestError, match="duplicate signal_model_id"):
        validate_signal_research_request(request)
