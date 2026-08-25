"""Trend-related Market Analysis components."""

from trading_framework.market_analysis.components.trend.ema import (
    EmaComponent,
    NumpyEmaImplementation,
)
from trading_framework.market_analysis.components.trend.slope import (
    NumpySlopeImplementation,
    SlopeComponent,
)

__all__ = [
    "EmaComponent",
    "NumpyEmaImplementation",
    "NumpySlopeImplementation",
    "SlopeComponent",
]
