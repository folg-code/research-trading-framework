"""NumPy-backed Market Analysis adapters."""

from trading_framework.market_analysis.adapters.numpy.kernels import (
    atr_sma,
    ema,
    ols_slope,
    true_range,
)

__all__ = ["atr_sma", "ema", "ols_slope", "true_range"]
