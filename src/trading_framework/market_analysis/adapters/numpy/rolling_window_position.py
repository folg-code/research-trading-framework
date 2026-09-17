"""Causal rolling z-score/percentile position kernel (generic input series)."""

import math
from dataclasses import dataclass

import numpy as np

from trading_framework.market_analysis.adapters.numpy.kernels import rolling_population_stdev, sma

_SQRT_2 = math.sqrt(2.0)


def _scalar_normal_cdf(z: float) -> float:
    if math.isnan(z):
        return math.nan
    return 0.5 * (1.0 + math.erf(z / _SQRT_2))


_normal_cdf = np.vectorize(_scalar_normal_cdf)


@dataclass(frozen=True, slots=True)
class RollingWindowPositionArrays:
    z_score: np.ndarray
    percentile: np.ndarray


def rolling_window_position(
    values: np.ndarray,
    *,
    window: int,
    method: str,
) -> RollingWindowPositionArrays:
    """Causal position of ``values[i]`` within its own trailing
    ``window``-bar window (statistics.rolling_window_position, IDEA-030):

        mean[i]    = sma(values, window)[i]
        stdev[i]   = rolling_population_stdev(values, window)[i]
        z_score[i] = (values[i] - mean[i]) / stdev[i]

    ``percentile`` depends on ``method`` -- these are kept as explicit,
    separate values (not conflated under one field, unlike the source
    material):

    - ``"normal"``: the standard-normal CDF of ``z_score`` -- a
      parametric approximation assuming the window is roughly
      normally distributed.
    - ``"empirical"``: the fraction of values in the window that are
      ``<= values[i]`` (an inclusive rolling rank), making no
      distributional assumption.

    Zero-variance convention: a perfectly flat window (population
    ``stdev == 0.0``) defines ``z_score = 0.0`` (this catalog's ordinary
    zero-denominator convention, D-S048-10) -- the value trivially equals
    its own window mean, a neutral position. The `"normal"`` percentile
    then falls out naturally as ``0.5`` (the CDF at ``z = 0``); the
    ``"empirical"`` percentile is unaffected by this convention since it
    never divides by ``stdev``.

    The first ``window - 1`` bars have no full window and are ``NaN`` for
    both outputs.
    """
    bar_count = int(values.shape[0])
    z_score = np.full(bar_count, np.nan, dtype=np.float64)
    percentile = np.full(bar_count, np.nan, dtype=np.float64)
    if bar_count < window or window < 2:
        return RollingWindowPositionArrays(z_score=z_score, percentile=percentile)

    mean = sma(values, window)
    stdev = rolling_population_stdev(values, window)
    with np.errstate(divide="ignore", invalid="ignore"):
        z_score = np.where(stdev == 0.0, 0.0, (values - mean) / stdev)
    # `mean`/`stdev` are already `NaN` before `window - 1`, and `NaN == 0.0`
    # is `False`, so the `else` branch (`NaN / NaN`) correctly leaves those
    # bars `NaN` without any extra masking.

    if method == "normal":
        percentile = _normal_cdf(z_score)
    else:
        windows = np.lib.stride_tricks.sliding_window_view(values, window)
        current = windows[:, -1]
        rank_count = (windows <= current[:, np.newaxis]).sum(axis=1)
        percentile[window - 1 :] = rank_count / window

    return RollingWindowPositionArrays(z_score=z_score, percentile=percentile)
