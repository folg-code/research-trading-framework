"""Market Model evaluator."""

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.market_model.results import market_model_result_dataframe
from trading_framework.model_expression.evaluation.evaluator import ExpressionEvaluator
from trading_framework.time.models.timeframe import Timeframe


class MarketModelEvaluator:
    """Evaluate one Market Model over a temporally aligned analysis frame."""

    def __init__(self, *, expression_evaluator: ExpressionEvaluator | None = None) -> None:
        self._expression_evaluator = expression_evaluator or ExpressionEvaluator()

    def evaluate(
        self,
        definition: MarketModelDefinition,
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
        return market_model_result_dataframe(
            market_model_id=definition.market_model_id,
            evaluation=evaluation,
        )
