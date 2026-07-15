"""Resolve canonical model aliases from a Signal Research definition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_COMBINED_SIGNAL_ID,
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    CANONICAL_SWING_COMPUTATION_TIMEFRAME,
    CANONICAL_SWING_PIVOT_RANGE,
    CANONICAL_VOLATILITY_PERIOD,
    CANONICAL_VOLATILITY_THRESHOLD,
    build_canonical_combined_signal,
    build_canonical_market_model_high_volatility,
    build_canonical_signal_high_volatility_on_true_edge,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.research.signal_research.definition import SignalResearchDefinitionSpec
from trading_framework.signal_model.definitions import SignalModelDefinition

MarketModelBuilder = Callable[..., MarketModelDefinition]
SignalModelBuilder = Callable[..., SignalModelDefinition]

_MARKET_MODEL_BUILDERS: dict[str, MarketModelBuilder] = {
    CANONICAL_MARKET_MODEL_ID: build_canonical_market_model_high_volatility,
    "high_volatility": build_canonical_market_model_high_volatility,
}

_SIGNAL_MODEL_BUILDERS: dict[str, SignalModelBuilder] = {
    CANONICAL_SIGNAL_HIGHER_LOW_ID: build_canonical_signal_higher_low_on_event,
    "higher_low_long": build_canonical_signal_higher_low_on_event,
    CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID: build_canonical_signal_high_volatility_on_true_edge,
    "high_volatility_long_edge": build_canonical_signal_high_volatility_on_true_edge,
    CANONICAL_COMBINED_SIGNAL_ID: build_canonical_combined_signal,
    "high_vol_and_higher_low": build_canonical_combined_signal,
}


class UnknownModelAliasError(ValidationError):
    """Raised when a definition references an unsupported model alias."""


@dataclass(frozen=True, slots=True)
class ResolvedModels:
    """Concrete model definitions and lineage metadata for one study."""

    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]
    resolved_parameters: dict[str, Any]
    component_lineage_hashes: dict[str, str]


def resolve_models_from_definition(
    spec: SignalResearchDefinitionSpec,
) -> ResolvedModels:
    """Resolve declared model aliases to canonical Sprint 006 builders."""
    market_models: list[MarketModelDefinition] = []
    signal_models: list[SignalModelDefinition] = []
    resolved_parameters: dict[str, Any] = {}
    lineage_hashes: dict[str, str] = {}

    if spec.market_model_id is not None:
        builder = _MARKET_MODEL_BUILDERS.get(spec.market_model_id)
        if builder is None:
            msg = f"unsupported market_model alias: {spec.market_model_id!r}"
            raise UnknownModelAliasError(msg)
        market_model = builder()
        market_models.append(market_model)
        resolved_parameters["market_model"] = {
            "alias": spec.market_model_id,
            "market_model_id": market_model.market_model_id,
            "period": CANONICAL_VOLATILITY_PERIOD,
            "threshold": CANONICAL_VOLATILITY_THRESHOLD,
        }
        lineage_hashes["market_model"] = _lineage_hash(
            market_model.market_model_id,
            resolved_parameters["market_model"],
        )

    if spec.signal_model_id is not None:
        signal_builder = _SIGNAL_MODEL_BUILDERS.get(spec.signal_model_id)
        if signal_builder is None:
            msg = f"unsupported signal_model alias: {spec.signal_model_id!r}"
            raise UnknownModelAliasError(msg)
        signal_model = signal_builder()
        signal_models.append(signal_model)
        resolved_parameters["signal_model"] = {
            "alias": spec.signal_model_id,
            "signal_model_id": signal_model.signal_model_id,
            "pivot_range": CANONICAL_SWING_PIVOT_RANGE,
            "computation_timeframe": CANONICAL_SWING_COMPUTATION_TIMEFRAME.value,
            "volatility_period": CANONICAL_VOLATILITY_PERIOD,
            "volatility_threshold": CANONICAL_VOLATILITY_THRESHOLD,
        }
        lineage_hashes["signal_model"] = _lineage_hash(
            signal_model.signal_model_id,
            resolved_parameters["signal_model"],
        )

    return ResolvedModels(
        market_models=tuple(market_models),
        signal_models=tuple(signal_models),
        resolved_parameters=resolved_parameters,
        component_lineage_hashes=lineage_hashes,
    )


def _lineage_hash(model_id: str, parameters: dict[str, Any]) -> str:
    import hashlib
    import json

    payload = json.dumps(
        {"model_id": model_id, "parameters": parameters},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
