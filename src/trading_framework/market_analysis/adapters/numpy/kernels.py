"""Pure NumPy indicator kernels for Market Analysis adapters."""

import numpy as np


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Wilder true range; bar 0 uses ``close[0]`` as the prior close."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    result: np.ndarray = np.maximum(tr1, np.maximum(tr2, tr3))
    return result


def atr_sma(true_range_values: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average of true range (MVP ATR)."""
    out = np.full(true_range_values.shape, np.nan, dtype=np.float64)
    if true_range_values.size < period or period < 1:
        return out
    kernel = np.ones(period, dtype=np.float64) / period
    valid = np.convolve(true_range_values, kernel, mode="valid")
    out[period - 1 :] = valid
    return out


def ema(close: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average with SMA seed at index ``period - 1``."""
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size < period or period < 1:
        return out
    alpha = 2.0 / (period + 1.0)
    seed = float(np.mean(close[:period]))
    out[period - 1] = seed
    for index in range(period, close.size):
        out[index] = alpha * close[index] + (1.0 - alpha) * out[index - 1]
    return out
