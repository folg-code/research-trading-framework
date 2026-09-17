"""Causal Fibonacci retracement/extension level kernel."""

import numpy as np


def fibonacci_level(
    latest_swing_high_level: np.ndarray,
    latest_swing_low_level: np.ndarray,
    latest_swing_high_observed_index: np.ndarray,
    latest_swing_low_observed_index: np.ndarray,
    *,
    ratio: float,
    is_extension: bool,
) -> np.ndarray:
    """Causal Fibonacci retracement/extension level from ``structure.swing``'s
    latest confirmed swing high/low (IDEA-032).

    The "active leg" is the one ending at whichever swing extreme was most
    recently confirmed: an up-leg (``low -> high``) when the latest swing
    high's own observed index is more recent than the latest swing low's;
    a down-leg (``high -> low``) otherwise. ``NaN`` until both a swing high
    and a swing low have been confirmed at least once (no leg exists yet).

        range = high - low
        retracement[up-leg]   = high - ratio * range   (pulls back toward low)
        retracement[down-leg] = low  + ratio * range   (pulls back toward high)
        extension[up-leg]     = low  + ratio * range   (projects beyond high)
        extension[down-leg]   = high - ratio * range   (projects beyond low)

    Retracement and extension use the SAME two formulas, just swapped by
    direction -- an extension continues the leg's own original direction
    (``ratio > 1`` projects past the most recent extreme), a retracement
    reverses it (``ratio`` in ``[0, 1]`` stays within the leg's range). No
    zero-denominator case: this is a linear interpolation/extrapolation
    along ``range``, never a division.
    """
    is_up_leg = latest_swing_high_observed_index > latest_swing_low_observed_index
    price_range = latest_swing_high_level - latest_swing_low_level

    if is_extension:
        up_leg_value = latest_swing_low_level + ratio * price_range
        down_leg_value = latest_swing_high_level - ratio * price_range
    else:
        up_leg_value = latest_swing_high_level - ratio * price_range
        down_leg_value = latest_swing_low_level + ratio * price_range

    level = np.where(is_up_leg, up_leg_value, down_leg_value)
    no_leg_yet = np.isnan(latest_swing_high_level) | np.isnan(latest_swing_low_level)
    result: np.ndarray = np.where(no_leg_yet, np.nan, level)
    return result
