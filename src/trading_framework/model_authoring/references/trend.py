"""Trend component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.trend import (
    EmaComponent,
    EmaDistanceComponent,
    SlopeComponent,
)
from trading_framework.model_authoring.conditions import Condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.price import price
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def ema(*, period: int = 20, alias: str | None = None) -> Operand:
    """``trend.ema(period=20)`` on the evaluation grid."""
    component = EmaComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("value"),
            alias=alias,
        )
    )


def ema_distance(
    *,
    period: int = 20,
    atr_period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``trend.ema_distance(period=20, atr_period=14, timeframe=None)`` --
    signed ``(close - ema(period)) / atr(atr_period)``, on the evaluation
    grid."""
    component = EmaDistanceComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize(
                {"period": period, "atr_period": atr_period}
            ),
            output_id=OutputId("distance_atr"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )


def slope(*, period: int = 20, alias: str | None = None) -> Operand:
    """``trend.slope(period=20)`` OLS slope of close on the evaluation grid."""
    component = SlopeComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("value"),
            alias=alias,
        )
    )


def price_above_ema(*, period: int = 20) -> Condition:
    """``price.close > trend.ema(period)`` convenience condition."""
    return price.close > ema(period=period)
