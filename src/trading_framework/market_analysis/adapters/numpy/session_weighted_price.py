"""Causal session-anchored volume-weighted average price kernel."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SessionWeightedPriceArrays:
    """Aligned Session Weighted Price outputs (``NaN`` outside RTH)."""

    value: np.ndarray
    deviation: np.ndarray
    upper_band: np.ndarray
    lower_band: np.ndarray


def session_weighted_price(
    typical_price: np.ndarray,
    volume: np.ndarray,
    *,
    is_rth: np.ndarray,
    trading_day_ordinal: np.ndarray,
    band_multiplier: float,
) -> SessionWeightedPriceArrays:
    """Causal volume-weighted average price, accumulated from each RTH
    session's own start (not a fixed rolling window) -- the session-anchored
    counterpart to ``volume.rolling_weighted_price``.

    Same session-boundary convention as ``structure.session_range``: a new
    session starts at the first RTH bar of a trading day (or the first RTH
    bar after a non-RTH gap); every accumulator resets there. Outside RTH,
    every output is ``NaN`` (the session doesn't exist yet/has ended).

        value[i]      = sum(typical_price * volume, session-so-far)
                        / sum(volume, session-so-far)
        deviation[i]  = sqrt(max(0, sum(volume * typical_price**2,
                        session-so-far) / sum(volume, session-so-far)
                        - value[i]**2))
        upper_band[i] = value[i] + band_multiplier * deviation[i]
        lower_band[i] = value[i] - band_multiplier * deviation[i]

    ``deviation`` is computed from the sum-of-squares form (rather than
    re-accumulating ``(typical_price - value)**2`` per bar) so it can be
    updated incrementally in the same single causal pass, without
    re-reading the session's own history at each bar.

    Zero-volume convention: a session with no volume at all so far
    (``sum(volume) == 0``) leaves every output ``NaN`` for that bar -- the
    same deliberate divergence from this catalog's usual "0.0 on
    zero-denominator" convention as ``volume.rolling_weighted_price``,
    since these are raw price levels, not ratios.
    """
    bar_count = int(typical_price.shape[0])
    value = np.full(bar_count, np.nan, dtype=np.float64)
    deviation = np.full(bar_count, np.nan, dtype=np.float64)
    upper_band = np.full(bar_count, np.nan, dtype=np.float64)
    lower_band = np.full(bar_count, np.nan, dtype=np.float64)

    cumulative_volume = 0.0
    cumulative_price_volume = 0.0
    cumulative_price_squared_volume = 0.0

    for index in range(bar_count):
        if not is_rth[index]:
            continue
        new_session = (
            index == 0
            or not is_rth[index - 1]
            or trading_day_ordinal[index] != trading_day_ordinal[index - 1]
        )
        if new_session:
            cumulative_volume = 0.0
            cumulative_price_volume = 0.0
            cumulative_price_squared_volume = 0.0

        bar_volume = volume[index]
        bar_price = typical_price[index]
        cumulative_volume += bar_volume
        cumulative_price_volume += bar_price * bar_volume
        cumulative_price_squared_volume += bar_price * bar_price * bar_volume

        if cumulative_volume == 0.0:
            continue

        session_value = cumulative_price_volume / cumulative_volume
        raw_variance = (
            cumulative_price_squared_volume / cumulative_volume - session_value * session_value
        )
        session_deviation = np.sqrt(max(raw_variance, 0.0))

        value[index] = session_value
        deviation[index] = session_deviation
        upper_band[index] = session_value + band_multiplier * session_deviation
        lower_band[index] = session_value - band_multiplier * session_deviation

    return SessionWeightedPriceArrays(
        value=value, deviation=deviation, upper_band=upper_band, lower_band=lower_band
    )
