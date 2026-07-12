"""Sequential batch execution."""

from trading_framework.core.exceptions import TradingFrameworkError
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import (
    ImplementationExecutionError,
    OutputValidationError,
)
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning.plan import ExecutionPlan
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
    ) -> AnalysisWorkspace:
        workspace = AnalysisWorkspace(market_view)
        execution_cache = cache if cache is not None else ExecutionCache()
        bar_count = len(market_view)

        for node in plan.nodes:
            identity = node.computation_identity
            cached = execution_cache.get(identity)
            if cached is not None:
                workspace.register(cached)
                continue

            workspace_view = workspace.view_for(node.dependency_keys)
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

        return workspace
