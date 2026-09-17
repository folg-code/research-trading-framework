"""Causal, priority-ordered per-bar/side candle reversal pattern classifier."""

from dataclasses import dataclass

import numpy as np

NONE = 0.0
ENGULFING = 1.0
LEVEL_CLOSE_REVERSAL = 2.0
REJECTION_WICK = 3.0


@dataclass(frozen=True, slots=True)
class ReversalPatternArrays:
    bullish_pattern: np.ndarray
    bearish_pattern: np.ndarray


def reversal_pattern(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    latest_swing_high_level: np.ndarray,
    latest_swing_low_level: np.ndarray,
    upper_wick_ratio: np.ndarray,
    lower_wick_ratio: np.ndarray,
    body_ratio: np.ndarray,
    *,
    wick_ratio_threshold: float,
) -> ReversalPatternArrays:
    """Per D-P19-05: one label per bar/side, evaluated in fixed priority order
    (first match wins) -- ``engulfing`` > ``level_close_reversal`` >
    ``rejection_wick`` > ``none``.

    ``engulfing``: the current bar's body fully contains the *prior* bar's
    body and the two bars close in opposite directions.

    ``level_close_reversal``: the bar's high/low pierces the *prior* bar's
    latest confirmed ``structure.swing`` level, but the bar's own close
    reclaims the origin side -- the same "pierce, then close back" test as
    ``structure.level_sweep_rejection``, evaluated as a same-bar event (no
    multi-bar observation window) since this is a per-bar label, not a
    pending multi-bar event.

    ``rejection_wick``: a hammer-style single-bar rejection -- the
    rejecting wick is at least ``wick_ratio_threshold`` times the body,
    with the opposite wick no larger than the body itself. A zero-body bar
    (``body_ratio == 0.0``, a doji) has no body to reject against and never
    qualifies, regardless of wick size.

    ``none``: an explicit, always-assigned label for a fully-evaluated bar
    where no rule matched -- distinct from index 0, which has no prior bar
    to evaluate ``engulfing`` against and is left ``NaN`` (not yet
    warmed up), not labeled ``none``.
    """
    bar_count = int(close.shape[0])
    bullish_pattern = np.full(bar_count, np.nan, dtype=np.float64)
    bearish_pattern = np.full(bar_count, np.nan, dtype=np.float64)
    if bar_count < 2:
        return ReversalPatternArrays(
            bullish_pattern=bullish_pattern, bearish_pattern=bearish_pattern
        )

    body_low = np.minimum(open_, close)
    body_high = np.maximum(open_, close)
    is_bullish_bar = close > open_
    is_bearish_bar = close < open_

    prev_body_low = np.roll(body_low, 1)
    prev_body_high = np.roll(body_high, 1)
    prev_is_bullish_bar = np.roll(is_bullish_bar, 1)
    prev_is_bearish_bar = np.roll(is_bearish_bar, 1)
    contains_prior_body = (body_low <= prev_body_low) & (body_high >= prev_body_high)

    engulfing_bullish = is_bullish_bar & prev_is_bearish_bar & contains_prior_body
    engulfing_bearish = is_bearish_bar & prev_is_bullish_bar & contains_prior_body

    prev_swing_high_level = np.roll(latest_swing_high_level, 1)
    prev_swing_low_level = np.roll(latest_swing_low_level, 1)
    level_reversal_bearish = (
        ~np.isnan(prev_swing_high_level)
        & (high > prev_swing_high_level)
        & (close < prev_swing_high_level)
    )
    level_reversal_bullish = (
        ~np.isnan(prev_swing_low_level)
        & (low < prev_swing_low_level)
        & (close > prev_swing_low_level)
    )

    has_body = body_ratio > 0.0
    safe_body_ratio = np.where(has_body, body_ratio, 1.0)
    lower_to_body = np.where(has_body, lower_wick_ratio / safe_body_ratio, 0.0)
    upper_to_body = np.where(has_body, upper_wick_ratio / safe_body_ratio, 0.0)
    rejection_bullish = (
        has_body & (lower_to_body >= wick_ratio_threshold) & (upper_wick_ratio <= body_ratio)
    )
    rejection_bearish = (
        has_body & (upper_to_body >= wick_ratio_threshold) & (lower_wick_ratio <= body_ratio)
    )

    bullish_pattern[1:] = np.where(
        engulfing_bullish[1:],
        ENGULFING,
        np.where(
            level_reversal_bullish[1:],
            LEVEL_CLOSE_REVERSAL,
            np.where(rejection_bullish[1:], REJECTION_WICK, NONE),
        ),
    )
    bearish_pattern[1:] = np.where(
        engulfing_bearish[1:],
        ENGULFING,
        np.where(
            level_reversal_bearish[1:],
            LEVEL_CLOSE_REVERSAL,
            np.where(rejection_bearish[1:], REJECTION_WICK, NONE),
        ),
    )

    return ReversalPatternArrays(bullish_pattern=bullish_pattern, bearish_pattern=bearish_pattern)
