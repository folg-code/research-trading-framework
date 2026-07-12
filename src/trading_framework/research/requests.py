"""Scope-aware Signal Research request contract and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition
from trading_framework.research.scope import ResearchScope
from trading_framework.signal_model.definitions import SignalModelDefinition


class SignalResearchRequestError(ValidationError):
    """Raised when a Signal Research request fails scope or model validation."""


@dataclass(frozen=True, slots=True)
class SignalResearchRequest:
    """Scope-aware experiment specification for one Signal Research run."""

    scope: ResearchScope
    dataset_ref: DatasetRef
    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]
    outcome_definition: ForwardOutcomeDefinition

    @classmethod
    def signal_only(
        cls,
        *,
        dataset_ref: DatasetRef,
        signal_models: tuple[SignalModelDefinition, ...],
        outcome_definition: ForwardOutcomeDefinition,
    ) -> SignalResearchRequest:
        return cls(
            scope=ResearchScope.SIGNAL_MODEL_ONLY,
            dataset_ref=dataset_ref,
            market_models=(),
            signal_models=signal_models,
            outcome_definition=outcome_definition,
        )

    @classmethod
    def market_only(
        cls,
        *,
        dataset_ref: DatasetRef,
        market_models: tuple[MarketModelDefinition, ...],
        outcome_definition: ForwardOutcomeDefinition,
    ) -> SignalResearchRequest:
        return cls(
            scope=ResearchScope.MARKET_MODEL_ONLY,
            dataset_ref=dataset_ref,
            market_models=market_models,
            signal_models=(),
            outcome_definition=outcome_definition,
        )

    @classmethod
    def market_and_signal(
        cls,
        *,
        dataset_ref: DatasetRef,
        market_models: tuple[MarketModelDefinition, ...],
        signal_models: tuple[SignalModelDefinition, ...],
        outcome_definition: ForwardOutcomeDefinition,
    ) -> SignalResearchRequest:
        return cls(
            scope=ResearchScope.MARKET_AND_SIGNAL,
            dataset_ref=dataset_ref,
            market_models=market_models,
            signal_models=signal_models,
            outcome_definition=outcome_definition,
        )


def validate_signal_research_request(request: SignalResearchRequest) -> None:
    """Reject invalid scope and model combinations before computation."""
    _validate_unique_model_ids(request)
    _validate_scope_model_combination(request)


def _validate_unique_model_ids(request: SignalResearchRequest) -> None:
    market_ids = [model.market_model_id for model in request.market_models]
    if len(market_ids) != len(set(market_ids)):
        msg = "market_models must not contain duplicate market_model_id values"
        raise SignalResearchRequestError(msg)

    signal_ids = [model.signal_model_id for model in request.signal_models]
    if len(signal_ids) != len(set(signal_ids)):
        msg = "signal_models must not contain duplicate signal_model_id values"
        raise SignalResearchRequestError(msg)


def _validate_scope_model_combination(request: SignalResearchRequest) -> None:
    market_count = len(request.market_models)
    signal_count = len(request.signal_models)

    if request.scope is ResearchScope.SIGNAL_MODEL_ONLY:
        if market_count != 0:
            msg = "SIGNAL_MODEL_ONLY rejects market_models"
            raise SignalResearchRequestError(msg)
        if signal_count != 1:
            msg = "SIGNAL_MODEL_ONLY requires exactly one signal model"
            raise SignalResearchRequestError(msg)
        return

    if request.scope is ResearchScope.MARKET_MODEL_ONLY:
        if signal_count != 0:
            msg = "MARKET_MODEL_ONLY rejects signal_models"
            raise SignalResearchRequestError(msg)
        if market_count != 1:
            msg = "MARKET_MODEL_ONLY requires exactly one market model"
            raise SignalResearchRequestError(msg)
        return

    if request.scope is ResearchScope.MARKET_AND_SIGNAL:
        if market_count != 1:
            msg = "MARKET_AND_SIGNAL requires exactly one market model"
            raise SignalResearchRequestError(msg)
        if signal_count != 1:
            msg = "MARKET_AND_SIGNAL requires exactly one signal model"
            raise SignalResearchRequestError(msg)
        return

    assert_never(request.scope)
