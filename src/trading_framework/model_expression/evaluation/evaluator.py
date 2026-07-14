"""Evaluate expression AST with three-valued null semantics."""

import math
from typing import assert_never

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression.evaluation.column_resolver import FrameColumnResolver
from trading_framework.model_expression.evaluation.frame_adapter import build_evaluation_dataframe
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
    ComparisonOperator,
    Expression,
    NotExpression,
    OperandReference,
    OrExpression,
)
from trading_framework.time.models.timeframe import Timeframe


class ExpressionEvaluator:
    """Evaluate one boolean expression over an aligned analysis frame."""

    def __init__(self, *, column_resolver: FrameColumnResolver | None = None) -> None:
        self._column_resolver = column_resolver or FrameColumnResolver()

    def collect_operand_keys(
        self,
        expression: Expression,
        frame: AnalysisFrame,
    ) -> tuple[str, ...]:
        """Return sorted operand column keys required by one expression."""
        return self._collect_operand_keys(expression, frame)

    def evaluate(
        self,
        expression: Expression,
        frame: AnalysisFrame,
        *,
        evaluation_timeframe: Timeframe,
        evaluation_table: pl.DataFrame | None = None,
    ) -> pl.DataFrame:
        """Return timestamp, available_at and nullable ``model_result`` columns."""
        if evaluation_table is None:
            operand_keys = self._collect_operand_keys(expression, frame)
            table = build_evaluation_dataframe(
                frame,
                evaluation_timeframe=evaluation_timeframe,
                column_keys=operand_keys,
            )
        else:
            table = evaluation_table
        result = self._evaluate_node(expression, table, frame)
        return table.select("timestamp", "available_at").with_columns(result.alias("model_result"))

    def _collect_operand_keys(
        self,
        expression: Expression,
        frame: AnalysisFrame,
    ) -> tuple[str, ...]:
        keys: dict[str, str] = {}
        for reference in self._collect_operands(expression):
            column_key = self._column_resolver.resolve(reference, frame)
            keys[column_key] = column_key
        return tuple(keys[key] for key in sorted(keys))

    def _collect_operands(self, expression: Expression) -> tuple[OperandReference, ...]:
        if isinstance(expression, CompareExpression):
            return (expression.operand,)
        if isinstance(expression, BinaryCompareExpression):
            return (expression.left, expression.right)
        if isinstance(expression, AndExpression):
            return self._collect_operands(expression.left) + self._collect_operands(
                expression.right
            )
        if isinstance(expression, OrExpression):
            return self._collect_operands(expression.left) + self._collect_operands(
                expression.right
            )
        if isinstance(expression, NotExpression):
            return self._collect_operands(expression.operand)
        assert_never(expression)

    def _evaluate_node(
        self,
        expression: Expression,
        table: pl.DataFrame,
        frame: AnalysisFrame,
    ) -> pl.Series:
        if isinstance(expression, CompareExpression):
            return self._evaluate_compare(expression, table, frame)
        if isinstance(expression, BinaryCompareExpression):
            return self._evaluate_binary_compare(expression, table, frame)
        if isinstance(expression, AndExpression):
            left = self._evaluate_node(expression.left, table, frame)
            right = self._evaluate_node(expression.right, table, frame)
            return self._and_nullable(left, right)
        if isinstance(expression, OrExpression):
            left = self._evaluate_node(expression.left, table, frame)
            right = self._evaluate_node(expression.right, table, frame)
            return self._or_nullable(left, right)
        if isinstance(expression, NotExpression):
            return self._not_nullable(self._evaluate_node(expression.operand, table, frame))
        assert_never(expression)

    def _evaluate_compare(
        self,
        expression: CompareExpression,
        table: pl.DataFrame,
        frame: AnalysisFrame,
    ) -> pl.Series:
        column_key = self._column_resolver.resolve(expression.operand, frame)
        operand = table[column_key]
        if isinstance(expression.value, bool):
            return self._compare_bool(operand, expression.operator, expression.value)
        return self._compare_numeric(operand, expression.operator, float(expression.value))

    def _evaluate_binary_compare(
        self,
        expression: BinaryCompareExpression,
        table: pl.DataFrame,
        frame: AnalysisFrame,
    ) -> pl.Series:
        left_key = self._column_resolver.resolve(expression.left, frame)
        right_key = self._column_resolver.resolve(expression.right, frame)
        left = table[left_key]
        right = table[right_key]
        frame_df = pl.DataFrame({"left": left, "right": right})
        null_mask = pl.col("left").is_nan() | pl.col("right").is_nan()
        comparison = {
            ComparisonOperator.EQ: pl.col("left") == pl.col("right"),
            ComparisonOperator.NE: pl.col("left") != pl.col("right"),
            ComparisonOperator.GT: pl.col("left") > pl.col("right"),
            ComparisonOperator.GE: pl.col("left") >= pl.col("right"),
            ComparisonOperator.LT: pl.col("left") < pl.col("right"),
            ComparisonOperator.LE: pl.col("left") <= pl.col("right"),
        }[expression.operator]
        return frame_df.select(pl.when(null_mask).then(None).otherwise(comparison).alias("result"))[
            "result"
        ]

    def _compare_bool(
        self,
        operand: pl.Series,
        operator: ComparisonOperator,
        value: bool,
    ) -> pl.Series:
        if operator is ComparisonOperator.EQ:
            return self._compare_numeric(operand, ComparisonOperator.EQ, 1.0 if value else 0.0)
        if operator is ComparisonOperator.NE:
            return self._compare_numeric(operand, ComparisonOperator.NE, 1.0 if value else 0.0)
        msg = f"boolean compare requires EQ or NE, got {operator.value}"
        raise TypeError(msg)

    def _compare_numeric(
        self,
        operand: pl.Series,
        operator: ComparisonOperator,
        value: float,
    ) -> pl.Series:
        frame = pl.DataFrame({"value": operand})
        expr = pl.col("value").is_nan()
        comparison = {
            ComparisonOperator.EQ: pl.col("value") == value,
            ComparisonOperator.NE: pl.col("value") != value,
            ComparisonOperator.GT: pl.col("value") > value,
            ComparisonOperator.GE: pl.col("value") >= value,
            ComparisonOperator.LT: pl.col("value") < value,
            ComparisonOperator.LE: pl.col("value") <= value,
        }[operator]
        return frame.select(pl.when(expr).then(None).otherwise(comparison).alias("result"))[
            "result"
        ]

    def _and_nullable(self, left: pl.Series, right: pl.Series) -> pl.Series:
        frame = pl.DataFrame({"left": left, "right": right})
        return frame.select(
            pl.when(pl.col("left").eq(False))
            .then(False)
            .when(pl.col("right").eq(False))
            .then(False)
            .when(pl.col("left").is_null() | pl.col("right").is_null())
            .then(None)
            .otherwise(True)
            .alias("result")
        )["result"]

    def _or_nullable(self, left: pl.Series, right: pl.Series) -> pl.Series:
        frame = pl.DataFrame({"left": left, "right": right})
        return frame.select(
            pl.when(pl.col("left").eq(True))
            .then(True)
            .when(pl.col("right").eq(True))
            .then(True)
            .when(pl.col("left").is_null() | pl.col("right").is_null())
            .then(None)
            .otherwise(False)
            .alias("result")
        )["result"]

    def _not_nullable(self, operand: pl.Series) -> pl.Series:
        frame = pl.DataFrame({"value": operand})
        return frame.select(
            pl.when(pl.col("value").is_null())
            .then(None)
            .otherwise(~pl.col("value"))
            .alias("result")
        )["result"]

    @staticmethod
    def operand_series_is_null(values: tuple[float, ...]) -> tuple[bool, ...]:
        """Helper for tests: map frame float tuples to null flags."""
        return tuple(math.isnan(value) for value in values)
