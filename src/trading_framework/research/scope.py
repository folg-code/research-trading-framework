"""Explicit Signal Research scope."""

from enum import StrEnum


class ResearchScope(StrEnum):
    """Declared scope for one Signal Research run."""

    SIGNAL_MODEL_ONLY = "signal_model_only"
    MARKET_MODEL_ONLY = "market_model_only"
    MARKET_AND_SIGNAL = "market_and_signal"
