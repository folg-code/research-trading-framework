"""Volatility component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.model_authoring.conditions import Condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_authoring.states import VolatilityState
from trading_framework.model_expression.references import ComponentOutputReference


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
