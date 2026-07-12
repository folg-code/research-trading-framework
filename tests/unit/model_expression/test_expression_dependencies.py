"""Tests for model expression dependency extraction."""

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.model_expression import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
    ExpressionDependencyExtractor,
    MarketField,
    MarketFieldReference,
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


def _ema_reference() -> ComponentOutputReference:
    component = EmaComponent()
    return ComponentOutputReference(
        component_id=component.component_id,
        parameters=component.parameter_schema.canonicalize({"period": 20}),
        output_id=OutputId("value"),
    )


def test_extract_single_component_dependency() -> None:
    reference = _volatility_state_reference()
    expression = CompareExpression(
        operand=reference,
        operator=ComparisonOperator.EQ,
        value=1.0,
    )

    dependencies = ExpressionDependencyExtractor().extract(expression)

    assert len(dependencies.component_requests) == 1
    assert dependencies.component_requests[0] == reference.to_component_request()
    assert dependencies.market_fields == ()


def test_extract_market_field_dependency() -> None:
    expression = CompareExpression(
        operand=MarketFieldReference(field=MarketField.CLOSE),
        operator=ComparisonOperator.GT,
        value=100.0,
    )

    dependencies = ExpressionDependencyExtractor().extract(expression)

    assert dependencies.component_requests == ()
    assert dependencies.market_fields == (MarketField.CLOSE,)


def test_extract_deduplicates_shared_component_requests() -> None:
    reference = _volatility_state_reference()
    expression = AndExpression(
        left=CompareExpression(
            operand=reference,
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        right=CompareExpression(
            operand=reference,
            operator=ComparisonOperator.NE,
            value=0.0,
        ),
    )

    dependencies = ExpressionDependencyExtractor().extract(expression)

    assert len(dependencies.component_requests) == 1


def test_extract_multiple_distinct_component_requests() -> None:
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

    dependencies = ExpressionDependencyExtractor().extract(expression)

    assert len(dependencies.component_requests) == 2
    component_ids = {request.component_id for request in dependencies.component_requests}
    assert component_ids == {ComponentId("volatility.state"), ComponentId("structure.swing")}


def test_extract_distinguishes_parameters_and_timeframes() -> None:
    expression = AndExpression(
        left=CompareExpression(
            operand=_volatility_state_reference(threshold=5.0),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
        right=CompareExpression(
            operand=_volatility_state_reference(threshold=7.0),
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )

    dependencies = ExpressionDependencyExtractor().extract(expression)
    assert len(dependencies.component_requests) == 2


def test_extract_mixed_market_and_component_dependencies() -> None:
    expression = AndExpression(
        left=CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=100.0,
        ),
        right=CompareExpression(
            operand=_ema_reference(),
            operator=ComparisonOperator.LT,
            value=5000.0,
        ),
    )

    dependencies = ExpressionDependencyExtractor().extract(expression)

    assert len(dependencies.component_requests) == 1
    assert dependencies.market_fields == (MarketField.CLOSE,)
