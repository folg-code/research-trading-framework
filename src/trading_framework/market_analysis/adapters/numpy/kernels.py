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


def _rsi_from_wilder_averages(avg_gain: float, avg_loss: float) -> float:
    """Wilder RSI from a pair of smoothed averages, per D-S051-04.

    Two degenerate cases are handled explicitly, not as a side effect of
    IEEE-754 division: a flat window (``avg_gain == avg_loss == 0.0``) is
    genuinely undefined for ``rs = avg_gain / avg_loss`` and is defined as the
    neutral midpoint ``50.0``; a window with gains but no losses is defined as
    ``100.0`` rather than dividing by zero.
    """
    if avg_gain == 0.0 and avg_loss == 0.0:
        return 50.0
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def rsi_wilder(close: np.ndarray, period: int) -> np.ndarray:
    """Wilder-smoothed RSI (0..100) of ``close``, per D-S051-05.

    ``avg_gain``/``avg_loss`` are seeded as the simple average of the first
    ``period`` bar-over-bar gains/losses, then recursively smoothed with
    Wilder's ``alpha = 1/period``:

        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i]) / period
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))

    The first ``period`` bars are ``NaN`` (there is no diff before bar 0, and
    ``period`` diffs are needed to seed the averages) -- the first valid value
    is at index ``period``. This is the textbook Wilder method with no
    library-matching (D-S051-05): a single documented estimator, not tuned to
    any particular library's rounding.
    """
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size <= period or period < 2:
        return out
    diffs = np.diff(close)
    gains = np.where(diffs > 0.0, diffs, 0.0)
    losses = np.where(diffs < 0.0, -diffs, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    out[period] = _rsi_from_wilder_averages(avg_gain, avg_loss)
    for index in range(period, diffs.size):
        avg_gain = (avg_gain * (period - 1) + gains[index]) / period
        avg_loss = (avg_loss * (period - 1) + losses[index]) / period
        out[index + 1] = _rsi_from_wilder_averages(avg_gain, avg_loss)
    return out


def ols_slope(close: np.ndarray, period: int) -> np.ndarray:
    """Causal ordinary-least-squares slope of close versus bar index in ``period``."""
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size < period or period < 2:
        return out
    windows = np.lib.stride_tricks.sliding_window_view(close, period)
    x = np.arange(period, dtype=np.float64)
    x_centered = x - x.mean()
    denominator = float(np.dot(x_centered, x_centered))
    y_centered = windows - windows.mean(axis=1, keepdims=True)
    out[period - 1 :] = y_centered @ x_centered / denominator
    return out
