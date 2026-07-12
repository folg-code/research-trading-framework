"""Tests for model expression validation."""

import pytest

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_expression import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
    Expression,
    MarketField,
    MarketFieldReference,
    ModelExpressionValidationError,
    NotExpression,
    OrExpression,
    validate_expression,
)
from trading_framework.time.models.timeframe import Timeframe


def _volatility_state_reference(*, threshold: float = 5.0) -> ComponentOutputReference:
    component = VolatilityStateComponent()
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": threshold}),
        output_id=OutputId("state"),
    )


def _swing_higher_low_reference() -> ComponentOutputReference:
    component = SwingStructureComponent()
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize({"pivot_range": 15}),
        output_id=OutputId("higher_low_event"),
        computation_timeframe=Timeframe("5m"),
    )


def test_validate_known_component_output_passes() -> None:
    registry = default_mvp_registry()
    expression = CompareExpression(
        operand=_volatility_state_reference(),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    validate_expression(expression, registry)


def test_validate_market_field_passes() -> None:
    registry = default_mvp_registry()
    expression = CompareExpression(
        operand=MarketFieldReference(field=MarketField.CLOSE),
        operator=ComparisonOperator.GT,
        value=100.0,
    )
    validate_expression(expression, registry)


def test_validate_unknown_output_rejected() -> None:
    registry = default_mvp_registry()
    component = VolatilityStateComponent()
    reference = ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0}),
        output_id=OutputId("missing_output"),
    )
    expression = CompareExpression(
        operand=reference,
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(ModelExpressionValidationError, match="unknown output"):
        validate_expression(expression, registry)


def test_validate_unregistered_component_rejected() -> None:
    registry = default_mvp_registry()
    component = VolatilityStateComponent()
    reference = ComponentOutputReference(
        component_id=ComponentId("unknown.component"),
        parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0}),
        output_id=OutputId("state"),
    )
    expression = CompareExpression(
        operand=reference,
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(Exception, match="component not registered"):
        validate_expression(expression, registry)


def test_validate_boolean_compare_requires_eq_or_ne() -> None:
    registry = default_mvp_registry()
    expression = CompareExpression(
        operand=_volatility_state_reference(),
        operator=ComparisonOperator.GT,
        value=True,
    )
    with pytest.raises(ModelExpressionValidationError, match="boolean compare"):
        validate_expression(expression, registry)


def test_validate_expression_depth_limit() -> None:
    registry = default_mvp_registry()
    leaf: Expression = CompareExpression(
        operand=_volatility_state_reference(),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    expression: Expression = leaf
    for _ in range(8):
        expression = AndExpression(left=expression, right=leaf)

    with pytest.raises(ModelExpressionValidationError, match="maximum depth"):
        validate_expression(expression, registry, max_depth=8)


def test_validate_composed_expression_passes() -> None:
    registry = default_mvp_registry()
    expression = AndExpression(
        left=CompareExpression(
            operand=_volatility_state_reference(),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        right=CompareExpression(
            operand=_swing_higher_low_reference(),
            operator=ComparisonOperator.EQ,
            value=True,
        ),
    )
    validate_expression(expression, registry)


def test_validate_not_expression_passes() -> None:
    registry = default_mvp_registry()
    expression = NotExpression(
        operand=OrExpression(
            left=CompareExpression(
                operand=MarketFieldReference(field=MarketField.OPEN),
                operator=ComparisonOperator.EQ,
                value=0.0,
            ),
            right=CompareExpression(
                operand=_volatility_state_reference(),
                operator=ComparisonOperator.NE,
                value=False,
            ),
        )
    )
    validate_expression(expression, registry)
