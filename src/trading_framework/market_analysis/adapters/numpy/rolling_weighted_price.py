"""Causal rolling volume-weighted average price kernel."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class RollingWeightedPriceArrays:
    value: np.ndarray
    deviation: np.ndarray
    upper_band: np.ndarray
    lower_band: np.ndarray


def rolling_weighted_price(
    typical_price: np.ndarray,
    volume: np.ndarray,
    *,
    period: int,
    band_multiplier: float,
) -> RollingWeightedPriceArrays:
    """Causal rolling volume-weighted average price over a trailing
    ``period``-bar window, plus a volume-weighted deviation band.

        value[i]      = sum(typical_price * volume, window) / sum(volume, window)
        deviation[i]  = sqrt(sum(volume * (typical_price - value[i]) ** 2, window)
                             / sum(volume, window))
        upper_band[i] = value[i] + band_multiplier * deviation[i]
        lower_band[i] = value[i] - band_multiplier * deviation[i]

    ``window = [i - period + 1, i]``. Zero-volume-window convention: a
    window with ``sum(volume) == 0`` (every bar in it reported zero
    volume) leaves ``value``/``deviation``/both bands as ``NaN`` for that
    bar -- a DELIBERATE DIVERGENCE from this catalog's usual "0.0 on
    zero-denominator" convention (D-S048-10), because these outputs are
    raw price levels, not ratios/oscillators: ``0.0`` would not be a
    neutral reading here, it would be a fabricated price far from the
    market. No genuine trading data is expected to have zero volume across
    an entire window, so this is a data-integrity edge case, not a normal
    market state.

    The first ``period - 1`` bars have no full window and are ``NaN``.
    """
    bar_count = int(typical_price.shape[0])
    value = np.full(bar_count, np.nan, dtype=np.float64)
    deviation = np.full(bar_count, np.nan, dtype=np.float64)
    upper_band = np.full(bar_count, np.nan, dtype=np.float64)
    lower_band = np.full(bar_count, np.nan, dtype=np.float64)
    if bar_count < period or period < 1:
        return RollingWeightedPriceArrays(
            value=value, deviation=deviation, upper_band=upper_band, lower_band=lower_band
        )

    price_windows = np.lib.stride_tricks.sliding_window_view(typical_price, period)
    volume_windows = np.lib.stride_tricks.sliding_window_view(volume, period)
    volume_sum = volume_windows.sum(axis=1)
    has_volume = volume_sum > 0.0
    safe_volume_sum = np.where(has_volume, volume_sum, 1.0)

    weighted_price_sum = (price_windows * volume_windows).sum(axis=1)
    window_value = np.where(has_volume, weighted_price_sum / safe_volume_sum, np.nan)

    weighted_squared_deviation = (
        volume_windows * (price_windows - window_value[:, np.newaxis]) ** 2
    ).sum(axis=1)
    window_deviation = np.where(
        has_volume, np.sqrt(weighted_squared_deviation / safe_volume_sum), np.nan
    )

    value[period - 1 :] = window_value
    deviation[period - 1 :] = window_deviation
    upper_band[period - 1 :] = window_value + band_multiplier * window_deviation
    lower_band[period - 1 :] = window_value - band_multiplier * window_deviation

    return RollingWeightedPriceArrays(
        value=value, deviation=deviation, upper_band=upper_band, lower_band=lower_band
    )
