"""Tests for expression evaluation and null semantics."""

import math
from collections.abc import Callable
from datetime import timedelta

import pytest

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression import (
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    ExpressionEvaluator,
    MarketField,
    MarketFieldReference,
    ModelExpressionError,
    NotExpression,
    OrExpression,
)
from trading_framework.time.models.timeframe import Timeframe


def test_evaluate_compare_with_null_operand(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"volatility_state": (math.nan, 0.0, 1.0)})
    expression = CompareExpression(
        operand=MarketFieldReference(field=MarketField.CLOSE),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    frame = AnalysisFrame(
        timestamps=frame.timestamps,
        columns={"close": frame.columns["volatility_state"]},
        column_lineage={},
    )
    result = ExpressionEvaluator().evaluate(
        expression,
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    assert result["model_result"].is_null()[0]
    assert result["model_result"][1] is False
    assert result["model_result"][2] is True


def test_evaluate_three_valued_and_or_not(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(
        columns={
            "left": (0.0, 1.0, 1.0, math.nan),
            "right": (math.nan, 0.0, math.nan, 1.0),
        }
    )
    left = CompareExpression(
        operand=MarketFieldReference(field=MarketField.OPEN),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    right = CompareExpression(
        operand=MarketFieldReference(field=MarketField.HIGH),
        operator=ComparisonOperator.EQ,
        value=1.0,
    )
    frame = AnalysisFrame(
        timestamps=frame.timestamps,
        columns={"open": frame.columns["left"], "high": frame.columns["right"]},
        column_lineage={},
    )
    evaluator = ExpressionEvaluator()

    and_result = evaluator.evaluate(
        AndExpression(left=left, right=right),
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    assert and_result["model_result"].to_list() == [False, False, None, None]

    or_result = evaluator.evaluate(
        OrExpression(left=left, right=right),
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    assert or_result["model_result"].to_list() == [None, True, True, True]

    not_result = evaluator.evaluate(
        NotExpression(
            operand=CompareExpression(
                operand=MarketFieldReference(field=MarketField.OPEN),
                operator=ComparisonOperator.EQ,
                value=0.0,
            )
        ),
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    assert not_result["model_result"].to_list() == [False, True, True, None]


def test_available_at_derived_from_evaluation_timeframe(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (1.0, 2.0)})
    result = ExpressionEvaluator().evaluate(
        CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=0.0,
        ),
        frame,
        evaluation_timeframe=Timeframe("1m"),
    )
    assert result["available_at"][0] == frame.timestamps[0] + timedelta(
        seconds=Timeframe("1m").total_seconds
    )


def test_missing_market_field_raises(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"open": (1.0,)})
    with pytest.raises(ModelExpressionError, match="market field column not present"):
        ExpressionEvaluator().evaluate(
            CompareExpression(
                operand=MarketFieldReference(field=MarketField.CLOSE),
                operator=ComparisonOperator.EQ,
                value=1.0,
            ),
            frame,
            evaluation_timeframe=Timeframe("1m"),
        )
