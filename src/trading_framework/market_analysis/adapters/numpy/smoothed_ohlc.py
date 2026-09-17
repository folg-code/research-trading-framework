"""Causal smoothed OHLC ("Heikin-Ashi") transform kernel."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SmoothedOhlcArrays:
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray


def smoothed_ohlc(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> SmoothedOhlcArrays:
    """Causal smoothed-OHLC ("Heikin-Ashi") transform.

        smoothed_close[i] = (open[i] + high[i] + low[i] + close[i]) / 4
        smoothed_open[0]  = (open[0] + close[0]) / 2
        smoothed_open[i]  = (smoothed_open[i-1] + smoothed_close[i-1]) / 2, i > 0
        smoothed_high[i]  = max(high[i], smoothed_open[i], smoothed_close[i])
        smoothed_low[i]   = min(low[i], smoothed_open[i], smoothed_close[i])

    Fully causal and recursively defined from bar 0 -- no external period
    parameter, so there is no warm-up: every bar is valid the moment its
    own raw OHLC is available.
    """
    bar_count = int(close.shape[0])
    smoothed_close = (open_ + high + low + close) / 4.0
    smoothed_open = np.empty(bar_count, dtype=np.float64)
    if bar_count > 0:
        smoothed_open[0] = (open_[0] + close[0]) / 2.0
        for index in range(1, bar_count):
            smoothed_open[index] = (smoothed_open[index - 1] + smoothed_close[index - 1]) / 2.0
    smoothed_high = np.maximum(high, np.maximum(smoothed_open, smoothed_close))
    smoothed_low = np.minimum(low, np.minimum(smoothed_open, smoothed_close))

    return SmoothedOhlcArrays(
        open=smoothed_open,
        high=smoothed_high,
        low=smoothed_low,
        close=smoothed_close,
    )
