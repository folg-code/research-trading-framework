"""A fixture strategy file returning a StrategyModelDefinition that fails
`validate_strategy_model_definition` (a NEUTRAL-direction signal model, which
has no directional entry -- the framework's own validation message names
this, not a made-up one)."""

from decimal import Decimal

from trading_framework.model_authoring import (
    NEUTRAL,
    VolatilityState,
    market_model,
    signal_model,
    volatility,
)
from trading_framework.strategy import (
    FixedBarsExitModel,
    FixedQuantityRiskModel,
    StrategyModelDefinition,
)


def build_strategy() -> StrategyModelDefinition:
    market = market_model(
        "fixture_fails_validation_market",
        when=(volatility.state(period=14, threshold=5.0) == VolatilityState.HIGH),
    ).definition
    signal = signal_model(
        "fixture_fails_validation_signal",
        direction=NEUTRAL,
        when=(volatility.state(period=14, threshold=5.0) == VolatilityState.HIGH),
    ).definition
    return StrategyModelDefinition(
        strategy_model_id="fixture_fails_validation",
        market_model=market,
        signal_model=signal,
        exit_model=FixedBarsExitModel(exit_after_bars=5),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(1)),
    )
