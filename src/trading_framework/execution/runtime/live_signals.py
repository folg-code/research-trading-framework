"""Live signal evaluation over a shared Strategy Model definition.

Live paper trading is driven by :class:`StrategyModelDefinition` — the same
domain object Strategy Research simulates. Entry signals use the shared Market
Analysis + ``SignalModelEvaluator`` stack over a rolling closed-bar buffer
(full recompute each step).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import final

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.assembly.assembler import AnalysisFrameAssembler
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.execution.warmup import max_history_requirement
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    ExecutionPlan,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
)
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.model_expression.evaluation.evaluator import ExpressionEvaluator
from trading_framework.model_expression.evaluation.frame_adapter import build_evaluation_dataframe
from trading_framework.model_expression.planning import (
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.signal_model import SignalFiringPolicy, SignalModelEvaluator
from trading_framework.strategy import StrategyModelDefinition, validate_strategy_model_definition
from trading_framework.time.models.timeframe import Timeframe

_ENGINE_VERSION = "0.1.0"
_PLACEHOLDER_RANGE = TimeRange(
    start=datetime(2020, 1, 1, tzinfo=UTC),
    end=datetime(2020, 1, 1, 1, tzinfo=UTC),
)


@final
@dataclass(frozen=True, slots=True)
class LiveSignalEvaluation:
    """Evaluated live signal booleans for one runtime decision step."""

    entry_signal_active: bool
    exit_signal_active: bool
    condition_active: bool
    close: float
    ema_value: float | None


@final
@dataclass(frozen=True, slots=True)
class StrategyModelLiveSignalEvaluator:
    """Evaluate a :class:`StrategyModelDefinition` on closed bars for live paper.

    Builds an ``AnalysisFrame`` from preloaded closed bars and evaluates the
    Strategy Model signal with ``SignalModelEvaluator``. Exit signals from
    ``FixedBarsExitModel`` are applied by the runtime assembly
    (``_fixed_bar_exit_active``), not by this evaluator.
    """

    strategy_model: StrategyModelDefinition
    timeframe: Timeframe = field(default_factory=lambda: Timeframe("1m"))
    registry: ComponentRegistry | None = None
    required_closed_bars: int = 0

    def __post_init__(self) -> None:
        validate_strategy_model_definition(self.strategy_model)
        object.__setattr__(
            self,
            "required_closed_bars",
            required_closed_bars_for_strategy(
                self.strategy_model,
                timeframe=self.timeframe,
                registry=self.registry,
            ),
        )

    def evaluate(self, closed_bars: Sequence[MarketBar]) -> LiveSignalEvaluation:
        """Evaluate the latest closed bar against the shared Strategy Model."""
        if not closed_bars:
            msg = "closed_bars must contain at least one bar"
            raise ValidationError(msg)
        ordered = tuple(sorted(closed_bars, key=lambda bar: bar.observed_at))
        latest_close = float(ordered[-1].close.value)
        if len(ordered) < self.required_closed_bars:
            return LiveSignalEvaluation(
                entry_signal_active=False,
                exit_signal_active=False,
                condition_active=False,
                close=latest_close,
                ema_value=None,
            )
        condition, emissions = _evaluate_signal_on_bars(
            strategy_model=self.strategy_model,
            closed_bars=ordered,
            timeframe=self.timeframe,
            registry=self.registry or default_mvp_registry(),
        )
        return LiveSignalEvaluation(
            entry_signal_active=_latest_entry_active(emissions, ordered[-1]),
            exit_signal_active=False,
            condition_active=_latest_condition_active(condition),
            close=latest_close,
            ema_value=None,
        )


# Compatibility alias — prefer StrategyModelLiveSignalEvaluator.
EmaMomentumLiveSignalEvaluator = StrategyModelLiveSignalEvaluator


def required_closed_bars_for_strategy(
    strategy_model: StrategyModelDefinition,
    *,
    timeframe: Timeframe,
    registry: ComponentRegistry | None = None,
    firing_lookback_bars: int | None = None,
) -> int:
    """Return closed bars needed before live evaluation may emit entries."""
    validate_strategy_model_definition(strategy_model)
    component_registry = registry or default_mvp_registry()
    plan = _build_strategy_plan(
        strategy_model,
        timeframe=timeframe,
        registry=component_registry,
    )
    warmup_bars = max_history_requirement(plan, source_timeframe=timeframe)
    lookback = (
        firing_lookback_bars
        if firing_lookback_bars is not None
        else _default_firing_lookback(strategy_model.signal_model.firing_policy)
    )
    if lookback < 0:
        msg = "firing_lookback_bars must be non-negative"
        raise ValueError(msg)
    return warmup_bars + lookback


def resolve_live_closed_bar_window(
    *,
    required_bars: int,
    configured_cap: int,
) -> int:
    """Rolling buffer length: never drop below required warmup sizing."""
    if required_bars < 1:
        msg = "required_bars must be positive"
        raise ValueError(msg)
    if configured_cap < 1:
        msg = "configured_cap must be positive"
        raise ValueError(msg)
    return max(required_bars, configured_cap)


def _default_firing_lookback(policy: SignalFiringPolicy) -> int:
    if policy is SignalFiringPolicy.ON_TRUE_EDGE:
        return 1
    return 0


def _live_dataset_ref(*, timeframe: Timeframe) -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("LIVE"),
            data_type="ohlcv",
            timeframe=timeframe,
            provider="live",
            source_id="preloaded",
        ),
        version=1,
    )


def _build_strategy_plan(
    strategy_model: StrategyModelDefinition,
    *,
    timeframe: Timeframe,
    registry: ComponentRegistry,
) -> ExecutionPlan:
    dependencies = collect_model_dependencies(
        market_models=(strategy_model.market_model,),
        signal_models=(strategy_model.signal_model,),
    )
    dataset_ref = _live_dataset_ref(timeframe=timeframe)
    planning_context = PlanningContext(
        dataset_ref=dataset_ref,
        timeframe=timeframe,
        requested_range=_PLACEHOLDER_RANGE,
    )
    planning_requests = tuple(
        PlanningRequest.from_component_request(component_request)
        for component_request in dependencies.component_requests
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=dataset_ref,
        requested_range=_PLACEHOLDER_RANGE,
        source_timeframe=timeframe,
        component_requests=tuple(
            (component_request.component_id, component_request, None)
            for component_request in dependencies.component_requests
        ),
    )
    return DependencyPlanner(registry).build_plan(
        planning_context,
        planning_requests,
        resolved_plan=resolved_plan,
    )


def _evaluate_signal_on_bars(
    *,
    strategy_model: StrategyModelDefinition,
    closed_bars: tuple[MarketBar, ...],
    timeframe: Timeframe,
    registry: ComponentRegistry,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    dependencies = collect_model_dependencies(
        market_models=(strategy_model.market_model,),
        signal_models=(strategy_model.signal_model,),
    )
    frame_request = build_analysis_frame_request(dependencies)
    dataset_ref = _live_dataset_ref(timeframe=timeframe)
    requested_range = TimeRange(
        start=closed_bars[0].observed_at,
        end=closed_bars[-1].available_at,
    )
    planning_context = PlanningContext(
        dataset_ref=dataset_ref,
        timeframe=timeframe,
        requested_range=requested_range,
        evaluation_timeframe=timeframe,
    )
    planning_requests = tuple(
        PlanningRequest.from_component_request(component_request)
        for component_request in dependencies.component_requests
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=dataset_ref,
        requested_range=requested_range,
        source_timeframe=timeframe,
        component_requests=tuple(
            (component_request.component_id, component_request, None)
            for component_request in dependencies.component_requests
        ),
        evaluation_timeframe=timeframe,
    )
    plan = DependencyPlanner(registry).build_plan(
        planning_context,
        planning_requests,
        resolved_plan=resolved_plan,
    )
    market_view = AnalysisDataView.from_bars(closed_bars)
    context = AnalysisContext(
        dataset_ref=dataset_ref,
        timeframe=timeframe,
        requested_range=requested_range,
        computation_range=requested_range,
        engine_version=_ENGINE_VERSION,
        evaluation_timeframe=timeframe,
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=market_view,
        context=context,
    )
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        frame_request,
        evaluation_timeframe=timeframe,
        evaluation_range=requested_range,
    )
    expression_evaluator = ExpressionEvaluator()
    signal_evaluator = SignalModelEvaluator(expression_evaluator=expression_evaluator)
    evaluation_table = build_evaluation_dataframe(
        frame,
        evaluation_timeframe=timeframe,
        column_keys=expression_evaluator.collect_operand_keys(
            strategy_model.signal_model.expression,
            frame,
        ),
    )
    condition = signal_evaluator.evaluate_condition(
        strategy_model.signal_model,
        frame,
        evaluation_timeframe=timeframe,
        evaluation_table=evaluation_table,
    )
    emissions = signal_evaluator.evaluate_emissions(
        strategy_model.signal_model,
        frame,
        evaluation_timeframe=timeframe,
        condition=condition,
        evaluation_table=evaluation_table,
    )
    return condition, emissions


def _latest_condition_active(condition: pl.DataFrame) -> bool:
    if condition.is_empty():
        return False
    value = condition["condition_met"][-1]
    return bool(value) if value is not None else False


def _latest_entry_active(emissions: pl.DataFrame, latest_bar: MarketBar) -> bool:
    if emissions.is_empty():
        return False
    return any(ts == latest_bar.observed_at for ts in emissions["detected_at"].to_list())


# Re-export helpers used by application wiring (avoid application↔execution cycles).
__all__ = [
    "EmaMomentumLiveSignalEvaluator",
    "LiveSignalEvaluation",
    "StrategyModelLiveSignalEvaluator",
    "required_closed_bars_for_strategy",
    "resolve_live_closed_bar_window",
]
