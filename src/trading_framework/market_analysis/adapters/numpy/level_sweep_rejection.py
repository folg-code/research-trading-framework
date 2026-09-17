"""Causal level-sweep-rejection detection ("liquidity grab")."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class LevelSweepRejectionArrays:
    high_rejection_event: np.ndarray
    low_rejection_event: np.ndarray


def level_sweep_rejection(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    latest_swing_high_level: np.ndarray,
    latest_swing_low_level: np.ndarray,
    *,
    observation_window: int,
) -> LevelSweepRejectionArrays:
    """A level is pierced (bar's high/low breaches the *prior* bar's latest
    swing level) and price rejects back (closes on the origin side) within
    ``observation_window`` bars of the pierce, including the pierce bar
    itself."""
    bar_count = int(high.shape[0])
    high_rejection = np.zeros(bar_count, dtype=np.float64)
    low_rejection = np.zeros(bar_count, dtype=np.float64)

    pending_high_level = float("nan")
    pending_high_remaining = 0
    pending_low_level = float("nan")
    pending_low_remaining = 0

    for index in range(1, bar_count):
        level_high = latest_swing_high_level[index - 1]
        level_low = latest_swing_low_level[index - 1]

        # Resolve or expire a pending high-side sweep first.
        if not np.isnan(pending_high_level):
            if close[index] < pending_high_level:
                high_rejection[index] = 1.0
                pending_high_level = float("nan")
            else:
                pending_high_remaining -= 1
                if pending_high_remaining <= 0:
                    pending_high_level = float("nan")

        # A fresh pierce above the level (only if no sweep is already pending).
        if np.isnan(pending_high_level) and not np.isnan(level_high) and high[index] > level_high:
            if close[index] < level_high:
                high_rejection[index] = 1.0
            else:
                pending_high_level = level_high
                pending_high_remaining = observation_window

        # Mirror for the low side.
        if not np.isnan(pending_low_level):
            if close[index] > pending_low_level:
                low_rejection[index] = 1.0
                pending_low_level = float("nan")
            else:
                pending_low_remaining -= 1
                if pending_low_remaining <= 0:
                    pending_low_level = float("nan")

        if np.isnan(pending_low_level) and not np.isnan(level_low) and low[index] < level_low:
            if close[index] > level_low:
                low_rejection[index] = 1.0
            else:
                pending_low_level = level_low
                pending_low_remaining = observation_window

    return LevelSweepRejectionArrays(
        high_rejection_event=high_rejection,
        low_rejection_event=low_rejection,
    )
