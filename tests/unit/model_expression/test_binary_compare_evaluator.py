"""Tests for binary compare expression evaluation."""

import math
from collections.abc import Callable

from trading_framework.market_analysis import OutputId
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.model_expression import (
    BinaryCompareExpression,
    ComparisonOperator,
    ExpressionEvaluator,
    MarketField,
    MarketFieldReference,
)
from trading_framework.model_expression.references import ComponentOutputReference
from trading_framework.time.models.timeframe import Timeframe


def test_evaluate_binary_compare_close_above_ema(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(
        columns={
            "close": (100.0, 101.0, 99.0),
            "ema": (100.0, 100.5, 100.5),
        }
    )
    frame = AnalysisFrame(
        timestamps=frame.timestamps,
        columns={"close": frame.columns["close"], "ema_20": frame.columns["ema"]},
        column_lineage={},
    )
    component = EmaComponent()
    expression = BinaryCompareExpression(
        left=MarketFieldReference(field=MarketField.CLOSE),
        operator=ComparisonOperator.GT,
        right=ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": 20}),
            output_id=OutputId("value"),
            alias="ema_20",
        ),
    )

    result = ExpressionEvaluator().evaluate(
        expression,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )

    assert result["model_result"].to_list() == [False, True, False]


def test_evaluate_binary_compare_null_if_operand_null(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (math.nan, 100.0), "ema": (100.0, 100.0)})
    frame = AnalysisFrame(
        timestamps=frame.timestamps,
        columns={"close": frame.columns["close"], "ema_20": frame.columns["ema"]},
        column_lineage={},
    )
    component = EmaComponent()
    expression = BinaryCompareExpression(
        left=MarketFieldReference(field=MarketField.CLOSE),
        operator=ComparisonOperator.GT,
        right=ComponentOutputReference(
            component_id=component.component_id,
            parameters=component.parameter_schema.canonicalize({"period": 20}),
            output_id=OutputId("value"),
            alias="ema_20",
        ),
    )

    result = ExpressionEvaluator().evaluate(
        expression,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )

    assert result["model_result"].is_null()[0]
    assert result["model_result"][1] is False
