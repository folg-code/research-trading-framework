"""Timeframe role validation helpers."""

from trading_framework.core.exceptions import ValidationError
from trading_framework.time.models.timeframe import Timeframe


def validate_computation_timeframe(
    *,
    source_timeframe: Timeframe,
    computation_timeframe: Timeframe,
) -> None:
    """Ensure computation granularity is not finer than the source dataset."""
    if computation_timeframe.total_seconds < source_timeframe.total_seconds:
        msg = (
            "computation_timeframe must be coarser than or equal to source timeframe: "
            f"{computation_timeframe.value} vs {source_timeframe.value}"
        )
        raise ValidationError(msg)


def validate_evaluation_timeframe(
    *,
    source_timeframe: Timeframe,
    evaluation_timeframe: Timeframe,
) -> None:
    """Ensure the evaluation grid is not coarser than the source dataset."""
    if evaluation_timeframe.total_seconds > source_timeframe.total_seconds:
        msg = (
            "evaluation_timeframe cannot be coarser than source timeframe: "
            f"{evaluation_timeframe.value} vs {source_timeframe.value}"
        )
        raise ValidationError(msg)


def resolve_computation_timeframe(
    *,
    source_timeframe: Timeframe,
    requested: Timeframe | None,
) -> Timeframe:
    """Return explicit or default computation timeframe."""
    computation = requested or source_timeframe
    validate_computation_timeframe(
        source_timeframe=source_timeframe,
        computation_timeframe=computation,
    )
    return computation


def resolve_evaluation_timeframe(
    *,
    source_timeframe: Timeframe,
    requested: Timeframe | None,
) -> Timeframe:
    """Return explicit or default evaluation timeframe."""
    evaluation = requested or source_timeframe
    validate_evaluation_timeframe(
        source_timeframe=source_timeframe,
        evaluation_timeframe=evaluation,
    )
    return evaluation
