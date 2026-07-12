"""Tests for model bundle dependency planning."""

from trading_framework.market_analysis import ComponentId, OutputId
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.market_model import MarketModelDefinition
from trading_framework.model_expression import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
    merge_expression_dependencies,
)
from trading_framework.model_expression.dependencies import ExpressionDependencyExtractor
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.signal_model import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
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


def test_merge_expression_dependencies_deduplicates_shared_components() -> None:
    reference = _volatility_state_reference()
    left = ExpressionDependencyExtractor().extract(
        CompareExpression(
            operand=reference,
            operator=ComparisonOperator.EQ,
            value=1.0,
        )
    )
    right = ExpressionDependencyExtractor().extract(
        CompareExpression(
            operand=reference,
            operator=ComparisonOperator.NE,
            value=0.0,
        )
    )

    merged = merge_expression_dependencies(left, right)

    assert len(merged.component_requests) == 1
    assert len(merged.component_output_references) == 1
    assert merged.component_output_references[0] == reference


def test_collect_model_dependencies_merges_market_and_signal_models() -> None:
    volatility_reference = _volatility_state_reference()
    swing_reference = _swing_higher_low_reference()
    market_model = MarketModelDefinition(
        market_model_id="high_volatility",
        expression=CompareExpression(
            operand=volatility_reference,
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )
    signal_model = SignalModelDefinition(
        signal_model_id="higher_low_long",
        expression=CompareExpression(
            operand=swing_reference,
            operator=ComparisonOperator.EQ,
            value=True,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )

    dependencies = collect_model_dependencies(
        market_models=(market_model,),
        signal_models=(signal_model,),
    )

    component_ids = {request.component_id for request in dependencies.component_requests}
    assert component_ids == {ComponentId("volatility.state"), ComponentId("structure.swing")}
    assert dependencies.market_fields == ()


def test_build_analysis_frame_request_maps_component_and_market_fields() -> None:
    volatility_reference = _volatility_state_reference()
    expression = AndExpression(
        left=CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=100.0,
        ),
        right=CompareExpression(
            operand=volatility_reference,
            operator=ComparisonOperator.EQ,
            value=1.0,
        ),
    )
    dependencies = ExpressionDependencyExtractor().extract(expression)

    frame_request = build_analysis_frame_request(dependencies)

    assert frame_request.market_fields == ("close",)
    assert len(frame_request.analysis_columns) == 1
    assert frame_request.analysis_columns[0].output_id == OutputId("state")
