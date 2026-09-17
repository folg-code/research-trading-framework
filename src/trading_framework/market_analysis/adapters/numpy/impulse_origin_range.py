"""Causal impulse-origin-range detection and active/invalidated role state."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ImpulseOriginRangeArrays:
    """``origin_event``: 1.0 at the bar where a new origin range is confirmed
    (the bar immediately *after* the actual origin bar, since confirmation
    needs the impulse bar itself). ``origin_high``/``origin_low``/``role_active``:
    forward-filled state of the currently active origin range (``NaN`` before
    any origin has been confirmed)."""

    origin_event: np.ndarray
    origin_high: np.ndarray
    origin_low: np.ndarray
    role_active: np.ndarray


def impulse_origin_range(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    impulse_direction: np.ndarray,
) -> ImpulseOriginRangeArrays:
    bar_count = int(high.shape[0])
    origin_event = np.zeros(bar_count, dtype=np.float64)
    origin_high = np.full(bar_count, np.nan, dtype=np.float64)
    origin_low = np.full(bar_count, np.nan, dtype=np.float64)
    role_active = np.full(bar_count, np.nan, dtype=np.float64)

    active_high = float("nan")
    active_low = float("nan")
    active_role = float("nan")
    active_impulse_direction = float("nan")

    for index in range(1, bar_count):
        # 1. Check invalidation of the currently active range using this
        #    bar's close -- must run before a new origin can replace it.
        if active_role == 1.0 and (
            (active_impulse_direction > 0 and close[index] < active_low)
            or (active_impulse_direction < 0 and close[index] > active_high)
        ):
            active_role = 0.0

        # 2. Check for a new origin at this bar (replaces the active range).
        direction = impulse_direction[index]
        if direction != 0.0:
            prev_body = close[index - 1] - open_[index - 1]
            prev_direction = np.sign(prev_body)
            if prev_direction != 0.0 and prev_direction == -direction:
                origin_event[index] = 1.0
                active_high = high[index - 1]
                active_low = low[index - 1]
                active_role = 1.0
                active_impulse_direction = direction

        # 3. Record this bar's state (forward-fill semantics).
        origin_high[index] = active_high
        origin_low[index] = active_low
        role_active[index] = active_role

    return ImpulseOriginRangeArrays(
        origin_event=origin_event,
        origin_high=origin_high,
        origin_low=origin_low,
        role_active=role_active,
    )
