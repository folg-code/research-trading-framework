"""Structure component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.references.timeframe import parse_timeframe
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def higher_low_event(
    *,
    pivot_range: int = 15,
    timeframe: str | Timeframe = "5m",
    alias: str | None = None,
) -> Operand:
    """``structure.higher_low_event(pivot_range=15, timeframe='5m')``."""
    component = SwingStructureComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"pivot_range": pivot_range}),
            output_id=OutputId("higher_low_event"),
            computation_timeframe=parse_timeframe(timeframe),
            alias=alias,
        ),
        is_event=True,
    )
