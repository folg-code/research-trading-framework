"""Volatility component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    RangeExpansionComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.model_authoring.conditions import Condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_authoring.states import VolatilityState
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def true_range(*, alias: str | None = None) -> Operand:
    """``volatility.true_range()`` on the evaluation grid."""
    component = TrueRangeComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({}),
            output_id=OutputId("value"),
            alias=alias,
        )
    )


def atr(*, period: int = 14, alias: str | None = None) -> Operand:
    """``volatility.atr(period=14)`` on the evaluation grid."""
    component = AtrComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("value"),
            alias=alias,
        )
    )


def range_expansion(
    *,
    period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``volatility.range_expansion(period=14, timeframe=None)`` --
    dimensionless ``true_range(bar) / atr(period)``, on the evaluation
    grid."""
    component = RangeExpansionComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("ratio"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def state(
    *,
    period: int = 14,
    threshold: float = 2.0,
    alias: str | None = None,
) -> Operand:
    """``volatility.state(period=14, threshold=2.0)``."""
    component = VolatilityStateComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize(
                {"period": period, "threshold": threshold}
            ),
            output_id=OutputId("state"),
            alias=alias,
        )
    )


def high(*, period: int = 14, threshold: float = 2.0) -> Condition:
    """``volatility.state(...) == VolatilityState.HIGH``."""
    return state(period=period, threshold=threshold) == VolatilityState.HIGH
