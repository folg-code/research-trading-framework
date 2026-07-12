"""Evaluate declarative models against one shared Market Analysis run."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from trading_framework.application.market_analysis.run_analysis import (
    AnalysisRunResult,
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.market_model.evaluation import MarketModelEvaluator
from trading_framework.model_expression.errors import ModelExpressionError
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.model_expression.validation import validate_expression
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.signal_model.evaluation import SignalModelEvaluator
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class ModelEvaluationError(ModelExpressionError):
    """Raised when model evaluation orchestration fails."""


@dataclass(frozen=True, slots=True)
class EvaluateModelsRequest:
    """Input for one shared analysis run and model evaluation pass."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    market_models: tuple[MarketModelDefinition, ...] = ()
    signal_models: tuple[SignalModelDefinition, ...] = ()
    evaluation_timeframe: Timeframe | None = None
    session_resolver: TradingSessionResolver | None = None


@dataclass(frozen=True, slots=True)
class EvaluateModelsResult:
    """Outcome of one shared analysis run and model evaluations."""

    analysis: AnalysisRunResult
    market_model_results: dict[str, pl.DataFrame]
    signal_model_conditions: dict[str, pl.DataFrame]
    signal_model_emissions: dict[str, pl.DataFrame]


def evaluate_models(
    request: EvaluateModelsRequest,
    *,
    registry: ComponentRegistry | None = None,
) -> EvaluateModelsResult:
    """Run Market Analysis once and evaluate all requested models on one frame."""
    component_registry = registry or default_mvp_registry()
    _validate_models(
        market_models=request.market_models,
        signal_models=request.signal_models,
        registry=component_registry,
    )
    dependencies = collect_model_dependencies(
        market_models=request.market_models,
        signal_models=request.signal_models,
    )
    frame_request = build_analysis_frame_request(dependencies)
    analysis = run_analysis(
        RunAnalysisRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=request.requested_range,
            storage_root=request.storage_root,
            component_requests=dependencies.component_requests,
            frame_request=frame_request,
            evaluation_timeframe=request.evaluation_timeframe,
            session_resolver=request.session_resolver,
        ),
        registry=component_registry,
    )
    frame = _require_frame(analysis.frame)
    evaluation_timeframe = request.evaluation_timeframe or request.timeframe
    market_evaluator = MarketModelEvaluator()
    signal_evaluator = SignalModelEvaluator()
    market_results = {
        definition.market_model_id: market_evaluator.evaluate(
            definition,
            frame,
            evaluation_timeframe=evaluation_timeframe,
        )
        for definition in request.market_models
    }
    signal_conditions = {
        definition.signal_model_id: signal_evaluator.evaluate_condition(
            definition,
            frame,
            evaluation_timeframe=evaluation_timeframe,
        )
        for definition in request.signal_models
    }
    signal_emissions = {
        definition.signal_model_id: signal_evaluator.evaluate_emissions(
            definition,
            frame,
            evaluation_timeframe=evaluation_timeframe,
        )
        for definition in request.signal_models
    }
    return EvaluateModelsResult(
        analysis=analysis,
        market_model_results=market_results,
        signal_model_conditions=signal_conditions,
        signal_model_emissions=signal_emissions,
    )


def _validate_models(
    *,
    market_models: tuple[MarketModelDefinition, ...],
    signal_models: tuple[SignalModelDefinition, ...],
    registry: ComponentRegistry,
) -> None:
    for market_model in market_models:
        validate_expression(market_model.expression, registry)
    for signal_model in signal_models:
        validate_expression(signal_model.expression, registry)


def _require_frame(frame: AnalysisFrame | None) -> AnalysisFrame:
    if frame is None:
        msg = "model evaluation requires an assembled AnalysisFrame"
        raise ModelEvaluationError(msg)
    return frame
