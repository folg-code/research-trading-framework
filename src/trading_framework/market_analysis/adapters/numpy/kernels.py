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


def rolling_min(values: np.ndarray, period: int) -> np.ndarray:
    """Causal rolling minimum over the trailing ``period`` bars (inclusive).

    ``out[i] = min(values[i - period + 1 : i + 1])``; the first ``period - 1``
    bars have no full window and are ``NaN``.
    """
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < period or period < 1:
        return out
    windows = np.lib.stride_tricks.sliding_window_view(values, period)
    out[period - 1 :] = windows.min(axis=1)
    return out


def rolling_max(values: np.ndarray, period: int) -> np.ndarray:
    """Causal rolling maximum over the trailing ``period`` bars (inclusive).

    ``out[i] = max(values[i - period + 1 : i + 1])``; the first ``period - 1``
    bars have no full window and are ``NaN``.
    """
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < period or period < 1:
        return out
    windows = np.lib.stride_tricks.sliding_window_view(values, period)
    out[period - 1 :] = windows.max(axis=1)
    return out


def sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average of ``values`` over the trailing ``period`` bars.

    Generic causal SMA kernel, reused wherever a plain trailing average is
    needed (e.g. ``momentum.stochastic``'s ``%D``); assumes no ``NaN``s
    within the window it is applied to (callers slice off their own warm-up
    first, matching the ``ema`` kernel's usage convention in ``momentum.macd``).
    """
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < period or period < 1:
        return out
    kernel = np.ones(period, dtype=np.float64) / period
    valid = np.convolve(values, kernel, mode="valid")
    out[period - 1 :] = valid
    return out


def stochastic_percent_k(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int,
) -> np.ndarray:
    """Causal Stochastic %K over a rolling ``period``-bar high/low range.

        %K[i] = (close[i] - min(low[i-period+1:i+1]))
                / (max(high[i-period+1:i+1]) - min(low[i-period+1:i+1])) * 100

    Zero-range window convention -- a DELIBERATE DIVERGENCE from this
    project's usual 0.0-on-zero-denominator convention (``candle.wick``
    D-S047-10; ``trend.ema_distance`` / ``volatility.range_expansion``
    D-S048-10). When a window is genuinely flat
    (``max(high window) == min(low window)``), %K is defined as ``50.0``
    (the neutral midpoint), NOT ``0.0``. Reason (D-S051-04): %K == 0.0
    already means "close sits at the window's low" -- a real, actionable
    signal. Emitting ``0.0`` for a flat window would fabricate that same
    false "close is at the low" signal rather than merely avoid an
    ``inf``/``NaN`` from IEEE-754 division. **Do not "fix" this back to
    0.0 as an apparent inconsistency** -- see D-S051-04 in
    ``S051_WAVE0_DECISIONS.md``.
    """
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size < period or period < 1:
        return out
    lowest = rolling_min(low, period)
    highest = rolling_max(high, period)
    denominator = highest - lowest
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.where(
            denominator == 0.0,
            50.0,
            (close - lowest) / denominator * 100.0,
        )
    out[period - 1 :] = k[period - 1 :]
    return out


def log_returns(close: np.ndarray) -> np.ndarray:
    """Bar-over-bar log returns of ``close`` (D-S051-03: ``r_t = ln(close_t / close_{t-1})``).

    Loses one bar relative to ``close``: index 0 has no prior close and is
    ``NaN``; ``out[i] = log(close[i] / close[i - 1])`` for ``i >= 1``.
    """
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size < 2:
        return out
    with np.errstate(divide="ignore", invalid="ignore"):
        out[1:] = np.log(close[1:] / close[:-1])
    return out


def rolling_population_stdev(values: np.ndarray, period: int) -> np.ndarray:
    """Causal rolling POPULATION standard deviation (``ddof=0``) of ``values``.

    ``out[i] = population_stdev(values[i - period + 1 : i + 1])``. Population
    (not sample) moments throughout this catalog, per D-S051-05 -- one
    documented estimator, not tuned to any particular library's default
    (``numpy``'s ``ddof=0`` default is used explicitly, not implicitly).
    Assumes no ``NaN``s within the window it is applied to (callers slice off
    their own warm-up first, matching ``sma``'s usage convention).
    """
    out = np.full(values.shape, np.nan, dtype=np.float64)
    if values.size < period or period < 1:
        return out
    windows = np.lib.stride_tricks.sliding_window_view(values, period)
    out[period - 1 :] = windows.std(axis=1, ddof=0)
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
