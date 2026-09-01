"""A valid fixture strategy for the loader test matrix (S047-T004)."""

from __future__ import annotations

from trading_framework.strategy import StrategyModelDefinition, build_canonical_strategy_model


def build_strategy() -> StrategyModelDefinition:
    return build_canonical_strategy_model(strategy_model_id="fixture_valid_strategy")
