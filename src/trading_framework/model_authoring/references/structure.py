"""Structure component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
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
