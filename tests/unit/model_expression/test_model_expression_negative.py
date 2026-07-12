"""Negative and regression tests for model expression validation."""

import pytest

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.model_authoring import VolatilityState, market_model, volatility
from trading_framework.model_authoring.states import volatility_state_compare_value
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
    ModelExpressionValidationError,
    validate_expression,
)
from trading_framework.model_expression.errors import ModelExpressionValidationError as IrError


def test_volatility_state_normal_is_rejected_by_dsl() -> None:
    with pytest.raises(IrError, match="normal"):
        volatility_state_compare_value(VolatilityState.NORMAL)


def test_market_model_with_normal_state_fails_validation() -> None:
    with pytest.raises(IrError, match="normal"):
        market_model(
            "invalid",
            when=(volatility.state(period=14, threshold=2.0) == VolatilityState.NORMAL),
        )


def test_forbidden_market_field_not_in_enum() -> None:
    with pytest.raises(ValueError):
        MarketField("vwap")


def test_validate_unknown_component_output_before_evaluation() -> None:
    registry = default_mvp_registry()
    component = VolatilityStateComponent()
    expression = CompareExpression(
        operand=ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0}),
            output_id=OutputId("not_an_output"),
        ),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(ModelExpressionValidationError, match="unknown output"):
        validate_expression(expression, registry)


def test_validate_unregistered_component_before_evaluation() -> None:
    registry = default_mvp_registry()
    component = VolatilityStateComponent()
    expression = CompareExpression(
        operand=ComponentOutputReference(
            component_id=ComponentId("research.custom"),
            parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0}),
            output_id=OutputId("state"),
        ),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    with pytest.raises(Exception, match="component not registered"):
        validate_expression(expression, registry)


def test_market_field_reference_is_restricted_to_ohlcv() -> None:
    registry = default_mvp_registry()
    for field in (
        MarketField.OPEN,
        MarketField.HIGH,
        MarketField.LOW,
        MarketField.CLOSE,
        MarketField.VOLUME,
    ):
        validate_expression(
            CompareExpression(
                operand=MarketFieldReference(field=field),
                operator=ComparisonOperator.GT,
                value=0.0,
            ),
            registry,
        )
