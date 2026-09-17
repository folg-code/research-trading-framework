"""Trend-related Market Analysis components."""

from trading_framework.market_analysis.components.trend.ema import (
    EmaComponent,
    NumpyEmaImplementation,
)
from trading_framework.market_analysis.components.trend.ema_distance import (
    EmaDistanceComponent,
    NumpyEmaDistanceImplementation,
)
from trading_framework.market_analysis.components.trend.normalized_slope import (
    NormalizedSlopeComponent,
    NumpyNormalizedSlopeImplementation,
)
from trading_framework.market_analysis.components.trend.slope import (
    NumpySlopeImplementation,
    SlopeComponent,
)

__all__ = [
    "EmaComponent",
    "EmaDistanceComponent",
    "NormalizedSlopeComponent",
    "NumpyEmaDistanceImplementation",
    "NumpyEmaImplementation",
    "NumpyNormalizedSlopeImplementation",
    "NumpySlopeImplementation",
    "SlopeComponent",
]
