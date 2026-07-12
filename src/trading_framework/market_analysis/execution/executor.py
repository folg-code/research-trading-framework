"""Sequential batch execution."""

from trading_framework.core.exceptions import TradingFrameworkError
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.data.resample import resample_analysis_view
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import (
    ImplementationExecutionError,
    OutputValidationError,
)
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.identity.mtf import ResampleIdentity
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning.plan import ExecutionPlan, PlannedNode, ResampleNode
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace


class ExecutionCache:
    """In-memory exact-match cache scoped to one execution plan."""

    def __init__(self) -> None:
        self._entries: dict[str, AnalysisResult] = {}

    def get(self, identity: ComputationIdentity) -> AnalysisResult | None:
        return self._entries.get(identity.canonical_key())

    def put(self, identity: ComputationIdentity, result: AnalysisResult) -> None:
        self._entries[identity.canonical_key()] = result

    def __len__(self) -> int:
        return len(self._entries)


class ResampleCache:
    """In-memory resample-stage cache keyed by ``ResampleIdentity``."""

    def __init__(self) -> None:
        self._entries: dict[str, AnalysisDataView] = {}

    def get(self, identity: ResampleIdentity) -> AnalysisDataView | None:
        return self._entries.get(identity.canonical_key())

    def put(self, identity: ResampleIdentity, view: AnalysisDataView) -> None:
        self._entries[identity.canonical_key()] = view

    def __len__(self) -> int:
        return len(self._entries)


def validate_analysis_result(
    result: AnalysisResult,
    *,
    bar_count: int,
    component_id: ComponentId,
) -> None:
    if result.computation_identity.component_id != component_id:
        msg = "result identity does not match executed component"
        raise OutputValidationError(component_id, msg)

    for output_id, series in result.outputs.items():
        if series.length != bar_count:
            msg = f"output {output_id} length {series.length} != expected {bar_count}"
            raise OutputValidationError(component_id, msg)

    if result.validity.valid_from_index < result.warmup.warmup_bars:
        msg = "valid range must exclude warm-up bars"
        raise OutputValidationError(component_id, msg)


class SequentialBatchExecutor:
    """Executes one deterministic plan against a read-only market view."""

    def execute(
        self,
        plan: ExecutionPlan,
        *,
        market_view: AnalysisDataView,
        context: AnalysisContext,
        cache: ExecutionCache | None = None,
        resample_cache: ResampleCache | None = None,
        session_metadata: TradingSessionMetadata | None = None,
    ) -> AnalysisWorkspace:
        workspace = AnalysisWorkspace(market_view, session_metadata=session_metadata)
        execution_cache = cache if cache is not None else ExecutionCache()
        resample_stage_cache = resample_cache if resample_cache is not None else ResampleCache()

        for node in plan.nodes:
            if isinstance(node, ResampleNode):
                self._execute_resample_node(node, workspace, resample_stage_cache)
            elif isinstance(node, PlannedNode):
                self._execute_component_node(
                    node,
                    workspace=workspace,
                    context=context,
                    execution_cache=execution_cache,
                )

        return workspace

    def _execute_resample_node(
        self,
        node: ResampleNode,
        workspace: AnalysisWorkspace,
        resample_cache: ResampleCache,
    ) -> None:
        identity = node.resample_identity
        identity_key = identity.canonical_key()
        cached = resample_cache.get(identity)
        if cached is None:
            source_view = workspace.market_view_for(node.source_input_key)
            cached = resample_analysis_view(source_view, node.resample_spec)
            resample_cache.put(identity, cached)
        workspace.register_resampled_view(identity_key, cached)

    def _execute_component_node(
        self,
        node: PlannedNode,
        *,
        workspace: AnalysisWorkspace,
        context: AnalysisContext,
        execution_cache: ExecutionCache,
    ) -> None:
        identity = node.computation_identity
        cached = execution_cache.get(identity)
        if cached is not None:
            workspace.register(cached)
            return

        workspace_view = workspace.view_for(
            node.dependency_keys,
            input_identity_key=identity.input_identity_key,
            computation_timeframe=identity.computation_timeframe,
            planned_computation_identity=identity,
        )
        bar_count = len(workspace_view.market)
        try:
            result = node.implementation.compute(
                context,
                workspace_view,
                node.request.parameters,
            )
        except TradingFrameworkError:
            raise
        except Exception as exc:
            raise ImplementationExecutionError(
                component_id=node.component.component_id,
                computation_key=identity.canonical_key(),
                message=str(exc),
            ) from exc

        validate_analysis_result(
            result,
            bar_count=bar_count,
            component_id=node.component.component_id,
        )
        workspace.register(result)
        execution_cache.put(identity, result)
