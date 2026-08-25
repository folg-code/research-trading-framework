"""Causal running ES RTH session-range kernel."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SessionRangeArrays:
    """Aligned Session Range outputs (NaN outside RTH)."""

    session_open: np.ndarray
    session_high: np.ndarray
    session_low: np.ndarray
    session_close: np.ndarray
    session_range: np.ndarray
    session_completed: np.ndarray


def session_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    *,
    is_rth: np.ndarray,
    trading_day_ordinal: np.ndarray,
) -> SessionRangeArrays:
    """Running RTH OHLC/range; ``session_completed`` on a confirmed group end."""
    bar_count = int(open_.shape[0])
    session_open = np.full(bar_count, np.nan, dtype=np.float64)
    session_high = np.full(bar_count, np.nan, dtype=np.float64)
    session_low = np.full(bar_count, np.nan, dtype=np.float64)
    session_close = np.full(bar_count, np.nan, dtype=np.float64)
    session_range_values = np.full(bar_count, np.nan, dtype=np.float64)
    session_completed = np.full(bar_count, np.nan, dtype=np.float64)
    in_rth = np.asarray(is_rth, dtype=bool)
    days = np.asarray(trading_day_ordinal)

    for index in range(bar_count):
        if not in_rth[index]:
            continue
        new_session = index == 0 or (not in_rth[index - 1]) or days[index] != days[index - 1]
        if new_session:
            session_open[index] = open_[index]
            session_high[index] = high[index]
            session_low[index] = low[index]
        else:
            session_open[index] = session_open[index - 1]
            session_high[index] = max(session_high[index - 1], high[index])
            session_low[index] = min(session_low[index - 1], low[index])
        session_close[index] = close[index]
        session_range_values[index] = session_high[index] - session_low[index]
        session_completed[index] = 0.0

    for index in range(bar_count):
        if not in_rth[index]:
            continue
        if index + 1 >= bar_count:
            continue
        next_same_group = bool(in_rth[index + 1]) and days[index + 1] == days[index]
        if not next_same_group:
            session_completed[index] = 1.0

    return SessionRangeArrays(
        session_open=session_open,
        session_high=session_high,
        session_low=session_low,
        session_close=session_close,
        session_range=session_range_values,
        session_completed=session_completed,
    )
