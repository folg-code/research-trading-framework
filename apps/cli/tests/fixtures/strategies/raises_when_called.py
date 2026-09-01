"""A fixture strategy file whose `build_strategy()` raises when called (not on import)."""

from trading_framework.strategy import StrategyModelDefinition


def build_strategy() -> StrategyModelDefinition:
    raise RuntimeError("deliberate failure inside build_strategy() (fixture)")
