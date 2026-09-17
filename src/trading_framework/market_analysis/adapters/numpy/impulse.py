"""Shared directional-impulse detection (body move vs. an ATR multiple)."""

import numpy as np


def impulse_directions(
    open_: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    *,
    impulse_atr_multiple: float,
) -> np.ndarray:
    """``+1.0`` (bullish), ``-1.0`` (bearish), or ``0.0`` (no impulse) per bar.

    A bar is impulsive when its body ``|close - open|`` spans at least
    ``impulse_atr_multiple`` times the concurrent ATR. A bar with ``NaN``
    ATR (warmup) is never impulsive.
    """
    body = close - open_
    with np.errstate(invalid="ignore"):
        is_impulse = np.abs(body) >= (impulse_atr_multiple * atr)
    return np.where(is_impulse, np.sign(body), 0.0)
