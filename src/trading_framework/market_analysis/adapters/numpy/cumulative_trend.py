"""Causal cumulative volume-weighted price trend kernel (formerly "Price Volume Trend")."""

import numpy as np


def cumulative_trend(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """Cumulative volume signed by the bar-over-bar direction of price change.

        pct_change[i] = (close[i] - close[i-1]) / close[i-1], i >= 1
        value[0]      = 0.0
        value[i]      = value[i-1] + volume[i] * pct_change[i], i >= 1

    Zero-denominator convention: ``close[i-1] == 0.0`` defines
    ``pct_change[i] = 0.0`` (this catalog's ordinary zero-denominator
    convention, D-S048-10) -- a zero prior close is a degenerate input, not
    a genuine "no change" reading, but contributing nothing to the
    cumulative sum on that one bar is the least-surprising fallback.

    Fully causal from bar 0, no external period parameter, so there is no
    warm-up: every bar is valid immediately.
    """
    bar_count = int(close.shape[0])
    value = np.zeros(bar_count, dtype=np.float64)
    if bar_count < 2:
        return value

    prev_close = close[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_change = np.where(prev_close == 0.0, 0.0, (close[1:] - prev_close) / prev_close)
    signed_volume = volume[1:] * pct_change
    value[1:] = np.cumsum(signed_volume)
    return value
