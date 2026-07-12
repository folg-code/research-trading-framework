"""Timeframe parsing for model authoring DSL."""

from trading_framework.time.models.timeframe import Timeframe


def parse_timeframe(value: str | Timeframe | None) -> Timeframe | None:
    """Convert user timeframe input to a domain ``Timeframe``."""
    if value is None:
        return None
    if isinstance(value, Timeframe):
        return value
    return Timeframe(value)
