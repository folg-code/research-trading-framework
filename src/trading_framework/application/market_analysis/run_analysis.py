"""Run a complete Market Analysis workflow from a published dataset."""

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.market_analysis.load_data_view import (
    LoadAnalysisDataViewRequest,
    load_analysis_data_view,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.assembly.assembler import AnalysisFrameAssembler
from trading_framework.market_analysis.assembly.frame import AnalysisFrame, AnalysisFrameRequest
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.execution.warmup import (
    extend_computation_range,
    max_history_requirement,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
)
from trading_framework.market_analysis.planning.plan import ExecutionPlan
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver

ENGINE_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class RunAnalysisRequest:
    """Input for one analysis execution against a published dataset."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    component_requests: tuple[ComponentRequest, ...]
    frame_request: AnalysisFrameRequest | None = None
    evaluation_timeframe: Timeframe | None = None
    session_resolver: TradingSessionResolver | None = None
    preloaded_bars: tuple[MarketBar, ...] | None = None


@dataclass(frozen=True, slots=True)
class AnalysisRunResult:
    """Outcome of one analysis run without replacing modular access to workspace parts."""

    plan: ExecutionPlan
    workspace: AnalysisWorkspace
    frame: AnalysisFrame | None = None


def _plan_analysis_execution(
    request: RunAnalysisRequest,
    *,
    registry: ComponentRegistry,
) -> tuple[ExecutionPlan, TimeRange]:
    planning_context = PlanningContext(
        dataset_ref=request.dataset_ref,
        timeframe=request.timeframe,
        requested_range=request.requested_range,
        evaluation_timeframe=request.evaluation_timeframe,
    )
    planning_requests = tuple(
        PlanningRequest.from_component_request(component_request)
        for component_request in request.component_requests
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=request.dataset_ref,
        requested_range=request.requested_range,
        source_timeframe=request.timeframe,
        component_requests=tuple(
            (component_request.component_id, component_request, None)
            for component_request in request.component_requests
        ),
        evaluation_timeframe=request.evaluation_timeframe,
    )
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        planning_context,
        planning_requests,
        resolved_plan=resolved_plan,
    )
    warmup_bars = max_history_requirement(plan, source_timeframe=request.timeframe)
    computation_range = extend_computation_range(
        request.requested_range,
        warmup_bars=warmup_bars,
        timeframe=request.timeframe,
    )
    return plan, computation_range


def resolve_analysis_computation_range(
    request: RunAnalysisRequest,
    *,
    registry: ComponentRegistry | None = None,
) -> TimeRange:
    """Return the warmup-extended bar range required for one analysis run."""
    _, computation_range = _plan_analysis_execution(
        request,
        registry=registry or default_mvp_registry(),
    )
    return computation_range


def run_analysis(
    request: RunAnalysisRequest,
    *,
    registry: ComponentRegistry | None = None,
    engine_version: str = ENGINE_VERSION,
) -> AnalysisRunResult:
    """Load data, plan, execute and optionally assemble a consumer frame."""
    component_registry = registry or default_mvp_registry()
    plan, computation_range = _plan_analysis_execution(
        request,
        registry=component_registry,
    )
    market_view = load_analysis_data_view(
        LoadAnalysisDataViewRequest(
            dataset_ref=request.dataset_ref,
            computation_range=computation_range,
        ),
        storage_root=request.storage_root,
        preloaded_bars=request.preloaded_bars,
    )
    context = AnalysisContext(
        dataset_ref=request.dataset_ref,
        timeframe=request.timeframe,
        requested_range=request.requested_range,
        computation_range=computation_range,
        engine_version=engine_version,
        evaluation_timeframe=request.evaluation_timeframe,
    )
    session_metadata = None
    if request.session_resolver is not None:
        session_metadata = TradingSessionMetadata.resolve(
            market_view.timestamps,
            request.session_resolver,
        )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=market_view,
        context=context,
        session_metadata=session_metadata,
    )
    frame = None
    if request.frame_request is not None:
        frame = AnalysisFrameAssembler().assemble(
            workspace,
            request.frame_request,
            evaluation_timeframe=context.evaluation_timeframe,
            evaluation_range=context.requested_range,
        )
    return AnalysisRunResult(plan=plan, workspace=workspace, frame=frame)
