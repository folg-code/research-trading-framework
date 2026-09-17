"""Causal running/previous period-extreme kernel (day/week grouping)."""

from dataclasses import dataclass
from datetime import date

import numpy as np


def period_keys(trading_days: tuple[date, ...], *, period: str) -> np.ndarray:
    """Integer group key per bar: the trading-day ordinal, or an ISO (year, week) key."""
    if period == "day":
        return np.array([day.toordinal() for day in trading_days], dtype=np.int64)
    if period == "week":
        return np.array(
            [
                iso_year * 100 + iso_week
                for iso_year, iso_week, _ in (day.isocalendar() for day in trading_days)
            ],
            dtype=np.int64,
        )
    msg = f"unsupported period: {period!r}"
    raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PeriodExtremeArrays:
    """``current``: running extreme of the period so far. ``previous``: the last
    *fully closed* period's extreme, held constant until the next period closes
    (``NaN`` before any period has closed)."""

    current: np.ndarray
    previous: np.ndarray


def running_and_previous_period_extreme(
    values: np.ndarray,
    *,
    keys: np.ndarray,
    side: str,
) -> PeriodExtremeArrays:
    bar_count = int(values.shape[0])
    current = np.full(bar_count, np.nan, dtype=np.float64)
    previous = np.full(bar_count, np.nan, dtype=np.float64)
    is_high = side == "high"
    running = float("nan")
    last_completed = float("nan")

    for index in range(bar_count):
        if index == 0 or keys[index] != keys[index - 1]:
            if index > 0:
                last_completed = running
            running = values[index]
        else:
            running = max(running, values[index]) if is_high else min(running, values[index])
        current[index] = running
        previous[index] = last_completed

    return PeriodExtremeArrays(current=current, previous=previous)
