"""Request resolution before DAG planning."""

from dataclasses import dataclass

from trading_framework.market_analysis.identity.component import ComponentId, ImplementationId
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.timeframes import (
    resolve_computation_timeframe,
    resolve_evaluation_timeframe,
)
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class RunTimeframeContext:
    """Run-level timeframe roles derived from dataset and run request."""

    source_timeframe: Timeframe
    evaluation_timeframe: Timeframe


@dataclass(frozen=True, slots=True)
class ResolvedComponentRequest:
    """Planner/executor input with material timeframe context."""

    component_id: ComponentId
    request: ComponentRequest
    source_timeframe: Timeframe
    computation_timeframe: Timeframe
    evaluation_timeframe: Timeframe
    implementation_id: ImplementationId | None = None
    input_identity_key: str | None = None


class RequestResolver:
    """Resolves public requests into execution-ready timeframe context."""

    @staticmethod
    def run_context(
        *,
        source_timeframe: Timeframe,
        evaluation_timeframe: Timeframe | None = None,
    ) -> RunTimeframeContext:
        return RunTimeframeContext(
            source_timeframe=source_timeframe,
            evaluation_timeframe=resolve_evaluation_timeframe(
                source_timeframe=source_timeframe,
                requested=evaluation_timeframe,
            ),
        )

    @staticmethod
    def resolve_component(
        *,
        component_id: ComponentId,
        request: ComponentRequest,
        run_context: RunTimeframeContext,
        implementation_id: ImplementationId | None = None,
        input_identity_key: str | None = None,
    ) -> ResolvedComponentRequest:
        computation_timeframe = resolve_computation_timeframe(
            source_timeframe=run_context.source_timeframe,
            requested=request.computation_timeframe,
        )
        return ResolvedComponentRequest(
            component_id=component_id,
            request=request,
            source_timeframe=run_context.source_timeframe,
            computation_timeframe=computation_timeframe,
            evaluation_timeframe=run_context.evaluation_timeframe,
            implementation_id=implementation_id,
            input_identity_key=input_identity_key,
        )
