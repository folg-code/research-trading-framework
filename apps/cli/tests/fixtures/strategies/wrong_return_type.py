"""A fixture strategy file whose `build_strategy()` returns the wrong type."""


def build_strategy() -> dict:
    return {"not": "a StrategyModelDefinition"}
