"""Causal level role-reversal detection ("SR flip"): broken, then retested and held."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class LevelRoleReversalArrays:
    resistance_to_support_event: np.ndarray
    support_to_resistance_event: np.ndarray


def level_role_reversal(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    latest_swing_high_level: np.ndarray,
    latest_swing_low_level: np.ndarray,
    *,
    retest_window: int,
) -> LevelRoleReversalArrays:
    """A level is broken (close beyond it), then within ``retest_window``
    bars price retests it from the new side and *holds* (closes back on the
    new side, not breaking through again) -- the level's role flips."""
    bar_count = int(high.shape[0])
    resistance_to_support = np.zeros(bar_count, dtype=np.float64)
    support_to_resistance = np.zeros(bar_count, dtype=np.float64)

    pending_r2s_level = float("nan")
    pending_r2s_remaining = 0
    pending_s2r_level = float("nan")
    pending_s2r_remaining = 0

    for index in range(1, bar_count):
        level_high = latest_swing_high_level[index - 1]
        level_low = latest_swing_low_level[index - 1]

        # Resolve a pending resistance-broken-to-support retest.
        if not np.isnan(pending_r2s_level):
            if low[index] <= pending_r2s_level <= close[index]:
                resistance_to_support[index] = 1.0
                pending_r2s_level = float("nan")
            elif close[index] < pending_r2s_level:
                pending_r2s_level = float("nan")  # broke back through -- not confirmed
            else:
                pending_r2s_remaining -= 1
                if pending_r2s_remaining <= 0:
                    pending_r2s_level = float("nan")

        # A fresh close above resistance starts a pending retest.
        if np.isnan(pending_r2s_level) and not np.isnan(level_high) and close[index] > level_high:
            pending_r2s_level = level_high
            pending_r2s_remaining = retest_window

        # Mirror: support broken to resistance.
        if not np.isnan(pending_s2r_level):
            if close[index] <= pending_s2r_level <= high[index]:
                support_to_resistance[index] = 1.0
                pending_s2r_level = float("nan")
            elif close[index] > pending_s2r_level:
                pending_s2r_level = float("nan")
            else:
                pending_s2r_remaining -= 1
                if pending_s2r_remaining <= 0:
                    pending_s2r_level = float("nan")

        if np.isnan(pending_s2r_level) and not np.isnan(level_low) and close[index] < level_low:
            pending_s2r_level = level_low
            pending_s2r_remaining = retest_window

    return LevelRoleReversalArrays(
        resistance_to_support_event=resistance_to_support,
        support_to_resistance_event=support_to_resistance,
    )
