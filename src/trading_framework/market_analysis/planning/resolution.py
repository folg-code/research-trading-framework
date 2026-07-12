"""Request resolution before DAG planning."""

from collections.abc import Sequence
from dataclasses import dataclass

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.identity.component import ComponentId, ImplementationId
from trading_framework.market_analysis.identity.mtf import ResampleIdentity
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.market_analysis.models.time_range import TimeRange
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


@dataclass(frozen=True, slots=True)
class ResolvedResampleRequirement:
    """Explicit resampling requirement for one shared target timeframe."""

    resample_spec: ResampleSpec
    resample_identity: ResampleIdentity


@dataclass(frozen=True, slots=True)
class ResolvedComponentInput:
    """One resolved component request with optional resample dependency."""

    component_id: ComponentId
    request: ComponentRequest
    resolved: ResolvedComponentRequest
    resample_requirement: ResolvedResampleRequirement | None = None
    implementation_id: ImplementationId | None = None


@dataclass(frozen=True, slots=True)
class ResolvedInputPlan:
    """Explicit input plan consumed by the DAG planner.

    Future extension: choose a published higher-timeframe dataset instead of
    resampling when one matches ``ResampleSpec.target_timeframe``.
    """

    run_context: RunTimeframeContext
    dataset_ref: DatasetRef
    requested_range: TimeRange
    components: tuple[ResolvedComponentInput, ...]

    def resample_requirements(self) -> tuple[ResolvedResampleRequirement, ...]:
        seen: set[str] = set()
        requirements: list[ResolvedResampleRequirement] = []
        for component in self.components:
            if component.resample_requirement is None:
                continue
            key = component.resample_requirement.resample_identity.canonical_key()
            if key in seen:
                continue
            seen.add(key)
            requirements.append(component.resample_requirement)
        return tuple(requirements)


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

    @staticmethod
    def _resample_requirement(
        *,
        dataset_ref: DatasetRef,
        source_timeframe: Timeframe,
        target_timeframe: Timeframe,
        requested_range: TimeRange,
    ) -> ResolvedResampleRequirement:
        spec = ResampleSpec(target_timeframe=target_timeframe)
        identity = ResampleIdentity(
            dataset_ref=dataset_ref,
            source_timeframe=source_timeframe,
            target_timeframe=target_timeframe,
            resample_spec=spec,
            requested_range=requested_range,
        )
        return ResolvedResampleRequirement(resample_spec=spec, resample_identity=identity)

    @classmethod
    def resolve_input_plan(
        cls,
        *,
        dataset_ref: DatasetRef,
        requested_range: TimeRange,
        source_timeframe: Timeframe,
        component_requests: Sequence[tuple[ComponentId, ComponentRequest, ImplementationId | None]],
        evaluation_timeframe: Timeframe | None = None,
    ) -> ResolvedInputPlan:
        run_context = cls.run_context(
            source_timeframe=source_timeframe,
            evaluation_timeframe=evaluation_timeframe,
        )
        resolved_components: list[ResolvedComponentInput] = []
        for component_id, request, implementation_id in component_requests:
            computation_timeframe = resolve_computation_timeframe(
                source_timeframe=run_context.source_timeframe,
                requested=request.computation_timeframe,
            )
            resample_requirement: ResolvedResampleRequirement | None = None
            input_identity_key: str | None = None
            if computation_timeframe.total_seconds > run_context.source_timeframe.total_seconds:
                resample_requirement = cls._resample_requirement(
                    dataset_ref=dataset_ref,
                    source_timeframe=run_context.source_timeframe,
                    target_timeframe=computation_timeframe,
                    requested_range=requested_range,
                )
                input_identity_key = resample_requirement.resample_identity.canonical_key()
            resolved = cls.resolve_component(
                component_id=component_id,
                request=request,
                run_context=run_context,
                implementation_id=implementation_id,
                input_identity_key=input_identity_key,
            )
            resolved_components.append(
                ResolvedComponentInput(
                    component_id=component_id,
                    request=request,
                    resolved=resolved,
                    resample_requirement=resample_requirement,
                    implementation_id=implementation_id,
                )
            )
        return ResolvedInputPlan(
            run_context=run_context,
            dataset_ref=dataset_ref,
            requested_range=requested_range,
            components=tuple(resolved_components),
        )
