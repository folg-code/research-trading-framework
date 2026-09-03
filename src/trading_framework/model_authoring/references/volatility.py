"""Volatility component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    RangeExpansionComponent,
    RelativeVolatilityComponent,
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


def _relative_volatility_operand(
    output_id: str,
    *,
    period: int,
    baseline_period: int,
    timeframe: str | Timeframe | None,
    alias: str | None,
) -> Operand:
    component = RelativeVolatilityComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize(
                {"period": period, "baseline_period": baseline_period}
            ),
            output_id=OutputId(output_id),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def relative_volatility(
    *,
    period: int = 20,
    baseline_period: int = 100,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``volatility.relative_volatility(period=20, baseline_period=100)`` --
    rolling population standard deviation of log returns over ``period``, on
    the evaluation grid."""
    return _relative_volatility_operand(
        "value",
        period=period,
        baseline_period=baseline_period,
        timeframe=timeframe,
        alias=alias,
    )


def relative_volatility_ratio(
    *,
    period: int = 20,
    baseline_period: int = 100,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``volatility.relative_volatility_ratio(period=20, baseline_period=100)``
    -- ``value / baseline`` (the same population-stdev estimator over a
    wider ``baseline_period`` window). A zero baseline yields ``0.0``, the
    project's ordinary zero-denominator convention (D-S048-10) -- unlike
    ``momentum.stochastic_k``'s deliberate ``50.0`` divergence (D-S051-04),
    which does not apply here."""
    return _relative_volatility_operand(
        "ratio",
        period=period,
        baseline_period=baseline_period,
        timeframe=timeframe,
        alias=alias,
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
