"""Bar-local candle wick/body ratio kernel."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CandleWickArrays:
    """Aligned candle wick/body ratio outputs."""

    upper_wick_ratio: np.ndarray
    lower_wick_ratio: np.ndarray
    body_ratio: np.ndarray


def candle_wick(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> CandleWickArrays:
    """Bar-local upper/lower wick and body ratios of the bar's own range.

    ``upper_wick_ratio = (high - max(open, close)) / (high - low)``
    ``lower_wick_ratio = (min(open, close) - low) / (high - low)``
    ``body_ratio       = abs(close - open) / (high - low)``

    A zero-range bar (``high == low``, so open/close/high/low are all equal)
    has no wick and no body to express as a fraction of range. Rather than let
    the division produce ``NaN``, this defines all three ratios as ``0.0`` on
    a zero-range bar -- a documented convention, not an incidental NaN.
    """
    bar_range = high - low
    zero_range = bar_range == 0.0
    upper_wick = high - np.maximum(open_, close)
    lower_wick = np.minimum(open_, close) - low
    body = np.abs(close - open_)

    safe_range = np.where(zero_range, 1.0, bar_range)
    upper_wick_ratio = np.where(zero_range, 0.0, upper_wick / safe_range)
    lower_wick_ratio = np.where(zero_range, 0.0, lower_wick / safe_range)
    body_ratio = np.where(zero_range, 0.0, body / safe_range)

    return CandleWickArrays(
        upper_wick_ratio=upper_wick_ratio,
        lower_wick_ratio=lower_wick_ratio,
        body_ratio=body_ratio,
    )
