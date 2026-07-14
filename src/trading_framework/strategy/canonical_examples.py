"""Canonical Strategy Model examples for tests and vertical slices."""

from decimal import Decimal

from trading_framework.application.model_evaluation.canonical_examples import (
    CANONICAL_MARKET_MODEL_ID,
    CANONICAL_SIGNAL_HIGHER_LOW_ID,
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition

CANONICAL_STRATEGY_MODEL_ID = "high_vol_higher_low_fixed_exit"
CANONICAL_EXIT_AFTER_BARS = 10
CANONICAL_POSITION_QUANTITY = 1


def build_canonical_strategy_model(
    *,
    strategy_model_id: str = CANONICAL_STRATEGY_MODEL_ID,
    market_model_id: str = CANONICAL_MARKET_MODEL_ID,
    signal_model_id: str = CANONICAL_SIGNAL_HIGHER_LOW_ID,
    exit_after_bars: int = CANONICAL_EXIT_AFTER_BARS,
    quantity: int = CANONICAL_POSITION_QUANTITY,
) -> StrategyModelDefinition:
    """Canonical Sprint 013 vertical slice: high_vol x higher_low x fixed exit x fixed risk."""
    return StrategyModelDefinition(
        strategy_model_id=strategy_model_id,
        market_model=build_canonical_market_model_high_volatility(market_model_id=market_model_id),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id=signal_model_id),
        exit_model=FixedBarsExitModel(exit_after_bars=exit_after_bars),
        risk_model=FixedQuantityRiskModel(quantity=Decimal(quantity)),
    )
