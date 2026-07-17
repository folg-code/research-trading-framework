"""Shared Market Analysis + model evaluation context for repeated strategy runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    resolve_analysis_computation_range,
)
from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical_columnar,
)
from trading_framework.application.model_evaluation import EvaluateModelsRequest, evaluate_models
from trading_framework.application.model_evaluation.evaluate_models import EvaluateModelsResult
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.profiling import optional_phase
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.strategy.strategy_model import StrategyModelDefinition
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver


class SharedStrategyEvaluationError(ValidationError):
    """Raised when a shared evaluation context cannot be used for a strategy run."""


@dataclass(frozen=True, slots=True)
class SharedStrategyEvaluationContext:
    """Reusable OHLCV + model-evaluation artifacts for one market/signal pair.

    Safe to reuse across Strategy Research runs that share dataset, range, timeframe
    and identical market/signal model definitions (e.g. exit_after_bars sweeps).
    """

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    evaluation_timeframe: Timeframe
    storage_root: Path
    market_model: MarketModelDefinition
    signal_model: SignalModelDefinition
    preloaded_column_batch: OhlcvColumnBatch
    preloaded_view: AnalysisDataView
    evaluation: EvaluateModelsResult

    def matches_strategy_models(self, strategy_model: StrategyModelDefinition) -> bool:
        """Return True when market/signal definitions match this context."""
        return (
            strategy_model.market_model == self.market_model
            and strategy_model.signal_model == self.signal_model
        )

    def matches_request(
        self,
        *,
        dataset_ref: DatasetRef,
        timeframe: Timeframe,
        requested_range: TimeRange,
        storage_root: Path,
        evaluation_timeframe: Timeframe | None,
        strategy_model: StrategyModelDefinition,
    ) -> bool:
        """Return True when this context can satisfy one Strategy Research request."""
        resolved_evaluation_timeframe = evaluation_timeframe or timeframe
        return (
            dataset_ref == self.dataset_ref
            and timeframe == self.timeframe
            and requested_range == self.requested_range
            and storage_root == self.storage_root
            and resolved_evaluation_timeframe == self.evaluation_timeframe
            and self.matches_strategy_models(strategy_model)
        )


@dataclass
class SharedStrategyEvaluationCache:
    """In-memory cache of shared evaluation contexts keyed by range + models."""

    _contexts: dict[tuple[object, ...], SharedStrategyEvaluationContext]

    def __init__(self) -> None:
        self._contexts = {}

    def get_or_build(
        self,
        *,
        dataset_ref: DatasetRef,
        timeframe: Timeframe,
        requested_range: TimeRange,
        storage_root: Path,
        strategy_model: StrategyModelDefinition,
        evaluation_timeframe: Timeframe | None = None,
        session_resolver: TradingSessionResolver | None = None,
    ) -> SharedStrategyEvaluationContext:
        """Return a cached context or build one for this market/signal + range."""
        resolved_evaluation_timeframe = evaluation_timeframe or timeframe
        key = (
            str(dataset_ref),
            timeframe.value,
            requested_range.start,
            requested_range.end,
            str(storage_root),
            resolved_evaluation_timeframe.value,
            strategy_model.market_model,
            strategy_model.signal_model,
        )
        existing = self._contexts.get(key)
        if existing is not None:
            return existing
        context = build_shared_strategy_evaluation_context(
            dataset_ref=dataset_ref,
            timeframe=timeframe,
            requested_range=requested_range,
            storage_root=storage_root,
            market_model=strategy_model.market_model,
            signal_model=strategy_model.signal_model,
            evaluation_timeframe=resolved_evaluation_timeframe,
            session_resolver=session_resolver,
        )
        self._contexts[key] = context
        return context


def build_shared_strategy_evaluation_context(
    *,
    dataset_ref: DatasetRef,
    timeframe: Timeframe,
    requested_range: TimeRange,
    storage_root: Path,
    market_model: MarketModelDefinition,
    signal_model: SignalModelDefinition,
    evaluation_timeframe: Timeframe | None = None,
    session_resolver: TradingSessionResolver | None = None,
) -> SharedStrategyEvaluationContext:
    """Load OHLCV once and evaluate one market/signal pair for reuse."""
    resolved_evaluation_timeframe = evaluation_timeframe or timeframe
    dependencies = collect_model_dependencies(
        market_models=(market_model,),
        signal_models=(signal_model,),
    )
    frame_request = build_analysis_frame_request(dependencies)
    analysis_request = RunAnalysisRequest(
        dataset_ref=dataset_ref,
        timeframe=timeframe,
        requested_range=requested_range,
        storage_root=storage_root,
        component_requests=dependencies.component_requests,
        frame_request=frame_request,
        evaluation_timeframe=resolved_evaluation_timeframe,
        session_resolver=session_resolver,
    )
    with optional_phase("shared_evaluation.plan_computation_range"):
        computation_range = resolve_analysis_computation_range(analysis_request)
    with optional_phase("shared_evaluation.load_ohlcv"):
        preloaded_column_batch = query_historical_columnar(
            QueryHistoricalRequest(
                dataset_ref=dataset_ref,
                start_at=computation_range.start,
                end_at=computation_range.end,
            ),
            storage_root=storage_root,
        )
        preloaded_view = preloaded_column_batch.to_analysis_view()
    with optional_phase("shared_evaluation.evaluate_models"):
        evaluation = evaluate_models(
            EvaluateModelsRequest(
                dataset_ref=dataset_ref,
                timeframe=timeframe,
                requested_range=requested_range,
                storage_root=storage_root,
                market_models=(market_model,),
                signal_models=(signal_model,),
                evaluation_timeframe=resolved_evaluation_timeframe,
                session_resolver=session_resolver,
                preloaded_column_batch=preloaded_column_batch,
                preloaded_view=preloaded_view,
            )
        )
    return SharedStrategyEvaluationContext(
        dataset_ref=dataset_ref,
        timeframe=timeframe,
        requested_range=requested_range,
        evaluation_timeframe=resolved_evaluation_timeframe,
        storage_root=storage_root,
        market_model=market_model,
        signal_model=signal_model,
        preloaded_column_batch=preloaded_column_batch,
        preloaded_view=preloaded_view,
        evaluation=evaluation,
    )
