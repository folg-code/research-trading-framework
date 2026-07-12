"""Run a complete Market Analysis workflow from a published dataset."""

from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.market_analysis.load_data_view import (
    LoadAnalysisDataViewRequest,
    load_analysis_data_view,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.assembly.assembler import AnalysisFrameAssembler
from trading_framework.market_analysis.assembly.frame import AnalysisFrame, AnalysisFrameRequest
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
)
from trading_framework.market_analysis.planning.plan import ExecutionPlan
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe

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


@dataclass(frozen=True, slots=True)
class AnalysisRunResult:
    """Outcome of one analysis run without replacing modular access to workspace parts."""

    plan: ExecutionPlan
    workspace: AnalysisWorkspace
    frame: AnalysisFrame | None = None


def run_analysis(
    request: RunAnalysisRequest,
    *,
    registry: ComponentRegistry | None = None,
    engine_version: str = ENGINE_VERSION,
) -> AnalysisRunResult:
    """Load data, plan, execute and optionally assemble a consumer frame."""
    component_registry = registry or default_mvp_registry()
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
    planner = DependencyPlanner(component_registry)
    plan = planner.build_plan(planning_context, planning_requests)
    warmup_bars = max_history_requirement(plan)
    computation_range = extend_computation_range(
        request.requested_range,
        warmup_bars=warmup_bars,
        timeframe=request.timeframe,
    )
    market_view = load_analysis_data_view(
        LoadAnalysisDataViewRequest(
            dataset_ref=request.dataset_ref,
            computation_range=computation_range,
        ),
        storage_root=request.storage_root,
    )
    context = AnalysisContext(
        dataset_ref=request.dataset_ref,
        timeframe=request.timeframe,
        requested_range=request.requested_range,
        computation_range=computation_range,
        engine_version=engine_version,
        evaluation_timeframe=request.evaluation_timeframe,
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=market_view,
        context=context,
    )
    frame = None
    if request.frame_request is not None:
        frame = AnalysisFrameAssembler().assemble(workspace, request.frame_request)
    return AnalysisRunResult(plan=plan, workspace=workspace, frame=frame)
