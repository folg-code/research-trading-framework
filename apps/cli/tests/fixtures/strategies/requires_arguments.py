"""A fixture strategy file whose `build_strategy` requires arguments."""

from trading_framework.strategy import StrategyModelDefinition, build_canonical_strategy_model


def build_strategy(market_model_id, signal_model_id) -> StrategyModelDefinition:  # pragma: no cover
    return build_canonical_strategy_model(
        market_model_id=market_model_id, signal_model_id=signal_model_id
    )
