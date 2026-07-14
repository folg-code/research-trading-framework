"""Signal Model evaluator."""

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.model_expression.evaluation.evaluator import ExpressionEvaluator
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.signal_model.firing import apply_firing_policy
from trading_framework.signal_model.results import signal_model_condition_dataframe
from trading_framework.time.models.timeframe import Timeframe


class SignalModelEvaluator:
    """Evaluate one Signal Model condition over a temporally aligned analysis frame."""

    def __init__(self, *, expression_evaluator: ExpressionEvaluator | None = None) -> None:
        self._expression_evaluator = expression_evaluator or ExpressionEvaluator()

    def evaluate_condition(
        self,
        definition: SignalModelDefinition,
        frame: AnalysisFrame,
        *,
        evaluation_timeframe: Timeframe,
        evaluation_table: pl.DataFrame | None = None,
    ) -> pl.DataFrame:
        evaluation = self._expression_evaluator.evaluate(
            definition.expression,
            frame,
            evaluation_timeframe=evaluation_timeframe,
            evaluation_table=evaluation_table,
        )
        return signal_model_condition_dataframe(
            signal_model_id=definition.signal_model_id,
            evaluation=evaluation,
        )

    def evaluate_emissions(
        self,
        definition: SignalModelDefinition,
        frame: AnalysisFrame,
        *,
        evaluation_timeframe: Timeframe,
        condition: pl.DataFrame | None = None,
        evaluation_table: pl.DataFrame | None = None,
    ) -> pl.DataFrame:
        if condition is None:
            condition = self.evaluate_condition(
                definition,
                frame,
                evaluation_timeframe=evaluation_timeframe,
                evaluation_table=evaluation_table,
            )
        emissions = apply_firing_policy(
            condition["condition_met"],
            policy=definition.firing_policy,
        )
        return condition.filter(emissions).select(
            pl.col("timestamp").alias("detected_at"),
            "available_at",
            pl.lit(definition.signal_model_id).alias("signal_model_id"),
            pl.lit(definition.direction.value).alias("direction"),
            pl.lit(definition.firing_policy.value).alias("firing_policy"),
        )
