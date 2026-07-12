"""Temporal semantics regression tests for model expression evaluation."""

import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.components.volatility import VolatilityStateComponent
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    ComponentOutputReference,
    ExpressionEvaluator,
)
from trading_framework.time.models.timeframe import Timeframe


def test_model_result_available_at_follows_operand_availability(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    component = VolatilityStateComponent()
    frame = build_test_frame(columns={"vol_state": (math.nan, 0.0, 1.0, 1.0)})
    timestamps = frame.timestamps
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"vol_state": frame.columns["vol_state"]},
        column_lineage={},
    )
    expression = CompareExpression(
        operand=ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": 14, "threshold": 5.0}),
            output_id=OutputId("state"),
            alias="vol_state",
        ),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    result = ExpressionEvaluator().evaluate(
        expression,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    expected_available = [timestamp + timedelta(minutes=1) for timestamp in timestamps]
    assert result["available_at"].to_list() == expected_available
    assert result["available_at"].null_count() == 0


def test_evaluator_never_emits_before_timestamp(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    frame = build_test_frame(
        start=start,
        columns={"close": (100.0, 101.0)},
    )
    from trading_framework.model_expression import MarketField, MarketFieldReference

    result = ExpressionEvaluator().evaluate(
        CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=100.0,
        ),
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    for timestamp, available_at in zip(result["timestamp"], result["available_at"], strict=True):
        assert available_at >= timestamp
