"""Horizon string parsing for Signal Research definitions."""

from __future__ import annotations

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.timeframe import Timeframe


def horizon_to_bars(horizon: str, *, evaluation_timeframe: Timeframe) -> int:
    """Convert a horizon timeframe string to bar counts on the evaluation timeframe."""
    horizon_tf = Timeframe(horizon.strip().lower())
    if horizon_tf.is_event_level:
        msg = f"horizon must be a bar duration, not {horizon!r}"
        raise ValidationError(msg)
    if evaluation_timeframe.is_event_level:
        msg = "evaluation_timeframe must be a bar duration to convert horizons"
        raise ValidationError(msg)
    horizon_seconds = horizon_tf.total_seconds
    base_seconds = evaluation_timeframe.total_seconds
    if horizon_seconds % base_seconds != 0:
        msg = (
            f"horizon {horizon!r} is not an integer multiple of "
            f"evaluation timeframe {evaluation_timeframe.value!r}"
        )
        raise ValidationError(msg)
    bars = horizon_seconds // base_seconds
    if bars < 1:
        msg = f"horizon {horizon!r} must span at least one evaluation bar"
        raise ValidationError(msg)
    return bars


def horizons_to_bars(
    horizons: tuple[str, ...],
    *,
    evaluation_timeframe: Timeframe,
) -> tuple[int, ...]:
    """Convert horizon timeframe strings to unique sorted bar counts."""
    bars = tuple(
        sorted(
            {
                horizon_to_bars(horizon, evaluation_timeframe=evaluation_timeframe)
                for horizon in horizons
            }
        )
    )
    if not bars:
        msg = "horizons must contain at least one value"
        raise ValidationError(msg)
    return bars
