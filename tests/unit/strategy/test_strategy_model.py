"""Unit tests for Strategy Model composition."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
)
from trading_framework.model_authoring import ON_EVENT, signal_model, structure
from trading_framework.signal_model.definitions import SignalDirection
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
    StrategyModelDefinitionError,
    build_canonical_strategy_model,
    validate_strategy_model_definition,
)
from trading_framework.time.models.timeframe import Timeframe


def test_canonical_strategy_model_passes_validation() -> None:
    definition = build_canonical_strategy_model()
    validate_strategy_model_definition(definition)
    assert definition.strategy_model_id == "high_vol_higher_low_fixed_exit"


def test_strategy_model_rejects_neutral_signal_direction() -> None:
    market = build_canonical_market_model_high_volatility(market_model_id="m1")
    signal = signal_model(
        "s1",
        direction=SignalDirection.NEUTRAL,
        when=structure.higher_low_event(
            pivot_range=15,
            timeframe=Timeframe("5m"),
        ),
        firing=ON_EVENT,
    ).definition
    definition = StrategyModelDefinition(
        strategy_model_id="neutral_strategy",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=5),
        risk_model=FixedQuantityRiskModel(quantity=Decimal("1")),
    )
    with pytest.raises(StrategyModelDefinitionError, match="directional entry"):
        validate_strategy_model_definition(definition)


def test_strategy_model_requires_supported_exit_and_risk_implementations() -> None:
    definition = build_canonical_strategy_model()
    object.__setattr__(definition, "exit_model", object())
    with pytest.raises(StrategyModelDefinitionError, match="FixedBarsExitModel"):
        validate_strategy_model_definition(definition)
