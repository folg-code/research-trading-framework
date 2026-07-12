"""Domain enums for model authoring DSL."""

from enum import StrEnum

from trading_framework.model_expression.errors import ModelExpressionValidationError


class VolatilityState(StrEnum):
    """Semantic volatility state labels for ``volatility.state`` comparisons."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


def volatility_state_compare_value(state: VolatilityState) -> float:
    """Map semantic volatility state to the component ``state`` output value."""
    if state is VolatilityState.HIGH:
        return 1.0
    if state is VolatilityState.LOW:
        return 0.0
    msg = (
        "volatility.state MVP supports LOW and HIGH only; "
        f"{state.value!r} is not produced by the current component"
    )
    raise ModelExpressionValidationError(msg)
