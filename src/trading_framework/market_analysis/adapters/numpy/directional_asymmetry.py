"""Causal rolling directional (up-bar vs. down-bar) volatility asymmetry."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class DirectionalAsymmetryArrays:
    up_volatility: np.ndarray
    down_volatility: np.ndarray
    asymmetry: np.ndarray


def directional_asymmetry(
    per_bar_variance_term: np.ndarray,
    close: np.ndarray,
    *,
    period: int,
) -> DirectionalAsymmetryArrays:
    """Average range-based volatility over up-close and down-close bars in a
    rolling ``period``-bar window, plus their log-ratio asymmetry.

    A bar is "up" when ``close[j] > close[j-1]``, "down" when
    ``close[j] < close[j-1]``; a flat close (or the series' first bar, with
    no prior close) contributes to neither side. If a window has no bars of
    one side, that side's average is ``NaN`` and ``asymmetry`` is ``NaN`` --
    an asymmetry needs both sides to be meaningful. If both sides exist but
    ``down_volatility`` is exactly ``0.0`` (down bars were all flat-range),
    ``asymmetry = 0.0`` (ordinary zero-denominator convention), not
    ``inf``.
    """
    bar_count = int(per_bar_variance_term.shape[0])
    up_volatility = np.full(bar_count, np.nan, dtype=np.float64)
    down_volatility = np.full(bar_count, np.nan, dtype=np.float64)
    asymmetry = np.full(bar_count, np.nan, dtype=np.float64)

    for index in range(period - 1, bar_count):
        window_start = index - period + 1
        up_sum = 0.0
        up_count = 0
        down_sum = 0.0
        down_count = 0
        for j in range(max(window_start, 1), index + 1):
            if close[j] > close[j - 1]:
                up_sum += per_bar_variance_term[j]
                up_count += 1
            elif close[j] < close[j - 1]:
                down_sum += per_bar_variance_term[j]
                down_count += 1

        if up_count > 0:
            up_volatility[index] = np.sqrt(max(up_sum / up_count, 0.0))
        if down_count > 0:
            down_volatility[index] = np.sqrt(max(down_sum / down_count, 0.0))

        if not np.isnan(up_volatility[index]) and not np.isnan(down_volatility[index]):
            if down_volatility[index] == 0.0:
                asymmetry[index] = 0.0
            else:
                asymmetry[index] = np.log(up_volatility[index] / down_volatility[index])

    return DirectionalAsymmetryArrays(
        up_volatility=up_volatility,
        down_volatility=down_volatility,
        asymmetry=asymmetry,
    )
