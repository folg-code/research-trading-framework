"""Compile and inspect authored models."""

from typing import assert_never

from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.model_expression.dependencies import (
    ExpressionDependencies,
    ExpressionDependencyExtractor,
)
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
    Expression,
    NotExpression,
    OrExpression,
)
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.signal_model.definitions import SignalFiringPolicy


def infer_firing_policy(
    expression: Expression,
    *,
    registry: ComponentRegistry,
) -> SignalFiringPolicy:
    """Infer ON_EVENT for event operands, otherwise ON_TRUE_EDGE."""
    del registry  # reserved for schema-backed event detection
    if _expression_has_event_output(expression):
        return SignalFiringPolicy.ON_EVENT
    return SignalFiringPolicy.ON_TRUE_EDGE


def collect_dependencies(expression: Expression) -> ExpressionDependencies:
    """Extract deduplicated analysis dependencies from a compiled expression."""
    return ExpressionDependencyExtractor().extract(expression)


def _expression_has_event_output(expression: Expression) -> bool:
    if isinstance(expression, CompareExpression):
        return _reference_is_event(expression.operand)
    if isinstance(expression, BinaryCompareExpression):
        return _reference_is_event(expression.left) or _reference_is_event(expression.right)
    if isinstance(expression, AndExpression):
        return _expression_has_event_output(expression.left) or _expression_has_event_output(
            expression.right
        )
    if isinstance(expression, OrExpression):
        return _expression_has_event_output(expression.left) or _expression_has_event_output(
            expression.right
        )
    if isinstance(expression, NotExpression):
        return _expression_has_event_output(expression.operand)
    assert_never(expression)


def _reference_is_event(reference: ComponentOutputReference | object) -> bool:
    if not isinstance(reference, ComponentOutputReference):
        return False
    return reference.output_id.value.endswith("_event")
