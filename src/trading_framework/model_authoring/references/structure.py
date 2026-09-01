"""Structure component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.structure import (
    LevelDistanceComponent,
    SessionRangeComponent,
    SwingStructureComponent,
)
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe

_DEFAULT_PIVOT_RANGE = 15
_DEFAULT_TIMEFRAME: str = "5m"


def _swing_operand(
    output_id: str,
    *,
    pivot_range: int,
    timeframe: str | Timeframe,
    alias: str | None,
    is_event: bool = False,
) -> Operand:
    component = SwingStructureComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"pivot_range": pivot_range}),
            output_id=OutputId(output_id),
            computation_timeframe=parse_timeframe(timeframe),
            alias=alias,
        ),
        is_event=is_event,
    )


def higher_high_event(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.higher_high_event(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "higher_high_event",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
        is_event=True,
    )


def higher_low_event(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.higher_low_event(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "higher_low_event",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
        is_event=True,
    )


def lower_high_event(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.lower_high_event(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "lower_high_event",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
        is_event=True,
    )


def lower_low_event(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.lower_low_event(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "lower_low_event",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
        is_event=True,
    )


def latest_higher_high_level(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.latest_higher_high_level(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "latest_higher_high_level",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
    )


def latest_higher_low_level(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.latest_higher_low_level(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "latest_higher_low_level",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
    )


def latest_lower_high_level(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.latest_lower_high_level(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "latest_lower_high_level",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
    )


def latest_lower_low_level(
    *,
    pivot_range: int = _DEFAULT_PIVOT_RANGE,
    timeframe: str | Timeframe = _DEFAULT_TIMEFRAME,
    alias: str | None = None,
) -> Operand:
    """``structure.latest_lower_low_level(pivot_range=15, timeframe='5m')``."""
    return _swing_operand(
        "latest_lower_low_level",
        pivot_range=pivot_range,
        timeframe=timeframe,
        alias=alias,
    )


def _session_range_operand(
    output_id: str,
    *,
    timeframe: str | Timeframe | None,
    alias: str | None,
    is_event: bool = False,
) -> Operand:
    component = SessionRangeComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({}),
            output_id=OutputId(output_id),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        ),
        is_event=is_event,
    )


def session_open(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_open()`` running RTH session open."""
    return _session_range_operand("session_open", timeframe=timeframe, alias=alias)


def session_high(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_high()`` running RTH session high."""
    return _session_range_operand("session_high", timeframe=timeframe, alias=alias)


def session_low(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_low()`` running RTH session low."""
    return _session_range_operand("session_low", timeframe=timeframe, alias=alias)


def session_close(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_close()`` running RTH session close."""
    return _session_range_operand("session_close", timeframe=timeframe, alias=alias)


def session_range(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_range()`` running RTH high minus low."""
    return _session_range_operand("session_range", timeframe=timeframe, alias=alias)


def session_completed(
    *,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.session_completed()`` 1.0 on a confirmed RTH session end."""
    return _session_range_operand(
        "session_completed",
        timeframe=timeframe,
        alias=alias,
        is_event=True,
    )


def _level_distance_operand(
    output_id: str,
    *,
    period: int,
    timeframe: str | Timeframe | None,
    alias: str | None,
) -> Operand:
    component = LevelDistanceComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId(output_id),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        ),
    )


def distance_to_session_high(
    *,
    period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.distance_to_session_high(period=14)`` ATR-normalized distance
    from close to the running RTH session high."""
    return _level_distance_operand(
        "distance_to_session_high_atr",
        period=period,
        timeframe=timeframe,
        alias=alias,
    )


def distance_to_session_low(
    *,
    period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``structure.distance_to_session_low(period=14)`` ATR-normalized distance
    from close to the running RTH session low."""
    return _level_distance_operand(
        "distance_to_session_low_atr",
        period=period,
        timeframe=timeframe,
        alias=alias,
    )
