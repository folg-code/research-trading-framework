"""Same-stem collision fixture A (S047-T004).

Must load independently of same_stem_b/strategy.py.
"""

from __future__ import annotations

from trading_framework.strategy import StrategyModelDefinition, build_canonical_strategy_model


def build_strategy() -> StrategyModelDefinition:
    return build_canonical_strategy_model(strategy_model_id="fixture_same_stem_a")
