"""Validate model expressions against registry contracts."""

from typing import assert_never

from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.model_expression.errors import ModelExpressionValidationError
from trading_framework.model_expression.expressions import (
    MAX_EXPRESSION_DEPTH,
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    Expression,
    NotExpression,
    OrExpression,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketFieldReference,
)

_BOOL_OPERATORS = frozenset({ComparisonOperator.EQ, ComparisonOperator.NE})
_ORDER_OPERATORS = frozenset(
    {
        ComparisonOperator.EQ,
        ComparisonOperator.NE,
        ComparisonOperator.GT,
        ComparisonOperator.GE,
        ComparisonOperator.LT,
        ComparisonOperator.LE,
    }
)


def validate_expression(
    expression: Expression,
    registry: ComponentRegistry,
    *,
    max_depth: int = MAX_EXPRESSION_DEPTH,
) -> None:
    """Validate expression shape, depth and registry-backed references."""
    _validate_node(expression, registry, depth=1, max_depth=max_depth)


def _validate_node(
    expression: Expression,
    registry: ComponentRegistry,
    *,
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth:
        msg = f"expression exceeds maximum depth {max_depth}"
        raise ModelExpressionValidationError(msg)

    if isinstance(expression, CompareExpression):
        _validate_compare(expression, registry)
        return

    if isinstance(expression, AndExpression):
        _validate_node(expression.left, registry, depth=depth + 1, max_depth=max_depth)
        _validate_node(expression.right, registry, depth=depth + 1, max_depth=max_depth)
        return

    if isinstance(expression, OrExpression):
        _validate_node(expression.left, registry, depth=depth + 1, max_depth=max_depth)
        _validate_node(expression.right, registry, depth=depth + 1, max_depth=max_depth)
        return

    if isinstance(expression, NotExpression):
        _validate_node(expression.operand, registry, depth=depth + 1, max_depth=max_depth)
        return

    assert_never(expression)


def _validate_compare(expression: CompareExpression, registry: ComponentRegistry) -> None:
    if isinstance(expression.value, bool):
        if expression.operator not in _BOOL_OPERATORS:
            msg = f"boolean compare requires EQ or NE, got {expression.operator.value}"
            raise ModelExpressionValidationError(msg)
    elif isinstance(expression.value, int | float):
        if expression.operator not in _ORDER_OPERATORS:
            msg = f"unsupported numeric compare operator: {expression.operator.value}"
            raise ModelExpressionValidationError(msg)
    else:
        assert_never(expression.value)

    operand = expression.operand
    if isinstance(operand, MarketFieldReference):
        return

    if isinstance(operand, ComponentOutputReference):
        _validate_component_output_reference(operand, registry)
        return

    assert_never(operand)


def _validate_component_output_reference(
    reference: ComponentOutputReference,
    registry: ComponentRegistry,
) -> None:
    component = registry.get_component(reference.component_id)
    output_ids = {field.output_id for field in component.output_schema.outputs}
    if reference.output_id not in output_ids:
        msg = (
            f"unknown output {reference.output_id!s} for component "
            f"{reference.component_id!s}; known outputs: "
            f"{sorted(output_id.value for output_id in output_ids)!r}"
        )
        raise ModelExpressionValidationError(msg)
