"""Swing structure detection kernel (reference loop implementation)."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SwingStructureResult:
    """Dense-grid swing events, classification events and forward-filled structural state."""

    swing_high_event: np.ndarray
    swing_low_event: np.ndarray
    swing_high_price: np.ndarray
    swing_low_price: np.ndarray
    swing_high_observed_index: np.ndarray
    swing_low_observed_index: np.ndarray
    latest_swing_high_level: np.ndarray
    latest_swing_low_level: np.ndarray
    latest_swing_high_observed_index: np.ndarray
    latest_swing_low_observed_index: np.ndarray
    higher_high_event: np.ndarray
    lower_high_event: np.ndarray
    higher_low_event: np.ndarray
    lower_low_event: np.ndarray
    latest_higher_high_level: np.ndarray
    latest_lower_high_level: np.ndarray
    latest_higher_low_level: np.ndarray
    latest_lower_low_level: np.ndarray
    latest_higher_high_observed_index: np.ndarray
    latest_lower_high_observed_index: np.ndarray
    latest_higher_low_observed_index: np.ndarray
    latest_lower_low_observed_index: np.ndarray


def _is_right_window_swing_high(
    high: np.ndarray,
    pivot_index: int,
    detection_index: int,
) -> bool:
    candidate = high[pivot_index]
    for index in range(pivot_index + 1, detection_index + 1):  # noqa: SIM110
        if high[index] > candidate:
            return False
    return True


def _is_right_window_swing_low(
    low: np.ndarray,
    pivot_index: int,
    detection_index: int,
) -> bool:
    candidate = low[pivot_index]
    for index in range(pivot_index + 1, detection_index + 1):  # noqa: SIM110
        if low[index] < candidate:
            return False
    return True


def detect_swing_structure(
    high: np.ndarray,
    low: np.ndarray,
    *,
    pivot_range: int,
) -> SwingStructureResult:
    """Detect right-window confirmed swings and derive structural classification state.

    Geometry (not symmetric local extrema): for available index ``t`` and
    ``pivot_range = pr``, candidate observed index is ``p = t - pr``.
    Confirmation uses bars ``[p .. t]`` only. Output is written at ``t``;
    observed index ``p`` is never back-written.

    Swing high when no bar in ``(p .. t]`` exceeds ``high[p]``.
    Swing low when no bar in ``(p .. t]`` goes below ``low[p]``.

    Classification uses strict ``>`` / ``<`` against the previous confirmed swing
    of the same type. Equal swings emit swing events and update ``latest_swing_*``
    but do not emit higher/lower classification events.
    """
    if pivot_range < 1:
        msg = "pivot_range must be >= 1"
        raise ValueError(msg)
    if high.shape != low.shape:
        msg = "high and low must have the same shape"
        raise ValueError(msg)
    if np.isnan(high).any() or np.isnan(low).any():
        msg = "high and low must not contain NaN"
        raise ValueError(msg)

    bar_count = high.size
    zeros = np.zeros(bar_count, dtype=np.float64)
    nan_row = np.full(bar_count, np.nan, dtype=np.float64)

    swing_high_event = zeros.copy()
    swing_low_event = zeros.copy()
    swing_high_price = nan_row.copy()
    swing_low_price = nan_row.copy()
    swing_high_observed_index = nan_row.copy()
    swing_low_observed_index = nan_row.copy()

    higher_high_event = zeros.copy()
    lower_high_event = zeros.copy()
    higher_low_event = zeros.copy()
    lower_low_event = zeros.copy()

    latest_swing_high_level = nan_row.copy()
    latest_swing_low_level = nan_row.copy()
    latest_swing_high_observed_index = nan_row.copy()
    latest_swing_low_observed_index = nan_row.copy()

    latest_higher_high_level = nan_row.copy()
    latest_lower_high_level = nan_row.copy()
    latest_higher_low_level = nan_row.copy()
    latest_lower_low_level = nan_row.copy()

    latest_higher_high_observed_index = nan_row.copy()
    latest_lower_high_observed_index = nan_row.copy()
    latest_higher_low_observed_index = nan_row.copy()
    latest_lower_low_observed_index = nan_row.copy()

    prev_confirmed_high = np.nan
    prev_confirmed_low = np.nan

    swing_high_level = np.nan
    swing_low_level = np.nan
    swing_high_observed = np.nan
    swing_low_observed = np.nan

    hh_level = np.nan
    lh_level = np.nan
    hl_level = np.nan
    ll_level = np.nan
    hh_observed = np.nan
    lh_observed = np.nan
    hl_observed = np.nan
    ll_observed = np.nan

    for detection_index in range(pivot_range, bar_count):
        pivot_index = detection_index - pivot_range
        swing_high_confirmed = _is_right_window_swing_high(high, pivot_index, detection_index)
        swing_low_confirmed = _is_right_window_swing_low(low, pivot_index, detection_index)

        if swing_high_confirmed:
            swing_price = high[pivot_index]
            swing_high_event[detection_index] = 1.0
            swing_high_price[detection_index] = swing_price
            swing_high_observed_index[detection_index] = float(pivot_index)
            swing_high_level = swing_price
            swing_high_observed = float(pivot_index)

            if not np.isnan(prev_confirmed_high):
                if swing_price > prev_confirmed_high:
                    higher_high_event[detection_index] = 1.0
                    hh_level = swing_price
                    hh_observed = float(pivot_index)
                elif swing_price < prev_confirmed_high:
                    lower_high_event[detection_index] = 1.0
                    lh_level = swing_price
                    lh_observed = float(pivot_index)
            prev_confirmed_high = swing_price

        if swing_low_confirmed:
            swing_price = low[pivot_index]
            swing_low_event[detection_index] = 1.0
            swing_low_price[detection_index] = swing_price
            swing_low_observed_index[detection_index] = float(pivot_index)
            swing_low_level = swing_price
            swing_low_observed = float(pivot_index)

            if not np.isnan(prev_confirmed_low):
                if swing_price < prev_confirmed_low:
                    lower_low_event[detection_index] = 1.0
                    ll_level = swing_price
                    ll_observed = float(pivot_index)
                elif swing_price > prev_confirmed_low:
                    higher_low_event[detection_index] = 1.0
                    hl_level = swing_price
                    hl_observed = float(pivot_index)
            prev_confirmed_low = swing_price

        latest_swing_high_level[detection_index] = swing_high_level
        latest_swing_low_level[detection_index] = swing_low_level
        latest_swing_high_observed_index[detection_index] = swing_high_observed
        latest_swing_low_observed_index[detection_index] = swing_low_observed

        latest_higher_high_level[detection_index] = hh_level
        latest_lower_high_level[detection_index] = lh_level
        latest_higher_low_level[detection_index] = hl_level
        latest_lower_low_level[detection_index] = ll_level

        latest_higher_high_observed_index[detection_index] = hh_observed
        latest_lower_high_observed_index[detection_index] = lh_observed
        latest_higher_low_observed_index[detection_index] = hl_observed
        latest_lower_low_observed_index[detection_index] = ll_observed

    return SwingStructureResult(
        swing_high_event=swing_high_event,
        swing_low_event=swing_low_event,
        swing_high_price=swing_high_price,
        swing_low_price=swing_low_price,
        swing_high_observed_index=swing_high_observed_index,
        swing_low_observed_index=swing_low_observed_index,
        latest_swing_high_level=latest_swing_high_level,
        latest_swing_low_level=latest_swing_low_level,
        latest_swing_high_observed_index=latest_swing_high_observed_index,
        latest_swing_low_observed_index=latest_swing_low_observed_index,
        higher_high_event=higher_high_event,
        lower_high_event=lower_high_event,
        higher_low_event=higher_low_event,
        lower_low_event=lower_low_event,
        latest_higher_high_level=latest_higher_high_level,
        latest_lower_high_level=latest_lower_high_level,
        latest_higher_low_level=latest_higher_low_level,
        latest_lower_low_level=latest_lower_low_level,
        latest_higher_high_observed_index=latest_higher_high_observed_index,
        latest_lower_high_observed_index=latest_lower_high_observed_index,
        latest_higher_low_observed_index=latest_higher_low_observed_index,
        latest_lower_low_observed_index=latest_lower_low_observed_index,
    )
