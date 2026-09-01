"""Candle component references."""

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.components.candle import CandleWickComponent
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_expression.references import ComponentOutputReference


def _wick_operand(output_id: str, *, alias: str | None) -> Operand:
    component = CandleWickComponent()
    return Operand(
        ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({}),
            output_id=OutputId(output_id),
            alias=alias,
        )
    )


def upper_wick_ratio(*, alias: str | None = None) -> Operand:
    """``candle.upper_wick_ratio()`` fraction of bar range above max(open, close)."""
    return _wick_operand("upper_wick_ratio", alias=alias)


def lower_wick_ratio(*, alias: str | None = None) -> Operand:
    """``candle.lower_wick_ratio()`` fraction of bar range below min(open, close)."""
    return _wick_operand("lower_wick_ratio", alias=alias)


def body_ratio(*, alias: str | None = None) -> Operand:
    """``candle.body_ratio()`` fraction of bar range spanned by the body."""
    return _wick_operand("body_ratio", alias=alias)
