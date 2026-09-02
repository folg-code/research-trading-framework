"""Momentum component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.momentum import RsiComponent
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def rsi(
    *,
    period: int = 14,
    timeframe: str | Timeframe | None = None,
    alias: str | None = None,
) -> Operand:
    """``momentum.rsi(period=14, timeframe=None)`` -- Wilder-smoothed RSI of
    close in ``[0, 100]``, on the evaluation grid."""
    component = RsiComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": period}),
            output_id=OutputId("value"),
            computation_timeframe=None if timeframe is None else parse_timeframe(timeframe),
            alias=alias,
        )
    )
