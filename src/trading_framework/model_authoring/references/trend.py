"""Trend component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.model_authoring.conditions import Condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.price import price
from trading_framework.model_expression.references import ComponentOutputReference


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


def price_above_ema(*, period: int = 20) -> Condition:
    """``price.close > trend.ema(period)`` convenience condition."""
    return price.close > ema(period=period)
