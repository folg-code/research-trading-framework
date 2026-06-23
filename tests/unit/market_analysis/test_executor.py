"""Sequential batch executor tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisResult,
    AvailabilityMetadata,
    AvailabilityPolicy,
    CanonicalParameters,
    Causality,
    ComponentId,
    ComponentKind,
    ComponentRequest,
    ComponentVersion,
    ComputationIdentity,
    DataFieldDependency,
    ExecutionPlan,
    HistoryRequirement,
    ImplementationId,
    ImplementationVersion,
    Lineage,
    OutputFieldSpec,
    OutputId,
    OutputSchema,
    OutputSeries,
    ParameterSchema,
    PlannedNode,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import (
    ImplementationExecutionError,
    OutputValidationError,
)
from trading_framework.market_analysis.execution import ExecutionCache, SequentialBatchExecutor
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView
from trading_framework.time.models.timeframe import Timeframe


class _ConstantComponent:
    component_id = ComponentId("price.close_copy")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(self, parameters: CanonicalParameters) -> tuple[()]:
        return ()


class _ConstantImplementation:
    implementation_id = ImplementationId("numpy.close_copy")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        bar_count = len(workspace.market)
        values = workspace.market.close.values
        identity = ComputationIdentity(
            component_id=ComponentId("price.close_copy"),
            component_version=ComponentVersion("1.0.0"),
            implementation_id=ImplementationId("numpy.close_copy"),
            implementation_version=ImplementationVersion("1.0.0"),
            parameters=parameters,
            dataset_ref=context.dataset_ref,
            timeframe=context.timeframe,
            requested_range=context.requested_range,
            dependency_keys=(),
        )
        output_id = OutputId("value")
        return AnalysisResult(
            computation_identity=identity,
            output_schema=OutputSchema(outputs=(OutputFieldSpec(output_id, "float64"),)),
            outputs={output_id: OutputSeries(values=values)},
            lineage=Lineage(
                dataset_ref=context.dataset_ref,
                component_id=ComponentId("price.close_copy"),
                component_version=ComponentVersion("1.0.0"),
                implementation_id=ImplementationId("numpy.close_copy"),
                implementation_version=ImplementationVersion("1.0.0"),
                parameters=parameters,
                dependency_keys=(),
                engine_version=context.engine_version,
                executed_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            validity=ValidityMetadata(valid_from_index=0, valid_to_index=bar_count - 1),
            warmup=WarmUpMetadata(
                warmup_bars=0,
                valid_from_index=0,
                valid_to_index=bar_count - 1,
            ),
            availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
            diagnostics={},
        )


class _FailingImplementation(_ConstantImplementation):
    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise RuntimeError("adapter failed")


def _market_view() -> AnalysisDataView:
    bars = []
    for minute in range(3):
        observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
        bars.append(
            MarketBar(
                open=Price(Decimal("100")),
                high=Price(Decimal("105")),
                low=Price(Decimal("99")),
                close=Price(Decimal(str(100 + minute))),
                volume=Volume(1000),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
    return AnalysisDataView.from_bars(bars)


def _context() -> AnalysisContext:
    dataset_ref = DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )
    time_range = TimeRange(
        start=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 12, 2, tzinfo=UTC),
    )
    return AnalysisContext(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=time_range,
        computation_range=time_range,
        engine_version="0.1.0",
    )


def _planned_node(implementation: _ConstantImplementation | _FailingImplementation) -> PlannedNode:
    component = _ConstantComponent()
    parameters = component.parameter_schema.canonicalize({})
    request = ComponentRequest(component_id=component.component_id, parameters=parameters)
    context = _context()
    identity = ComputationIdentity(
        component_id=component.component_id,
        component_version=component.component_version,
        implementation_id=implementation.implementation_id,
        implementation_version=implementation.implementation_version,
        parameters=parameters,
        dataset_ref=context.dataset_ref,
        timeframe=context.timeframe,
        requested_range=context.requested_range,
        dependency_keys=(),
    )
    return PlannedNode(
        request=request,
        component=component,
        implementation=implementation,
        computation_identity=identity,
        dependency_keys=(),
    )


def test_executor_registers_results_without_mutating_market_view() -> None:
    market_view = _market_view()
    original_close = market_view.close.values
    executor = SequentialBatchExecutor()
    workspace = executor.execute(
        ExecutionPlan(nodes=(_planned_node(_ConstantImplementation()),)),
        market_view=market_view,
        context=_context(),
    )
    assert market_view.close.values == original_close
    assert len(workspace.result_store) == 1


def test_execution_cache_skips_reexecution() -> None:
    call_count = 0

    class _CountingImplementation(_ConstantImplementation):
        def compute(
            self,
            context: AnalysisContext,
            workspace: AnalysisWorkspaceView,
            parameters: CanonicalParameters,
        ) -> AnalysisResult:
            nonlocal call_count
            call_count += 1
            return super().compute(context, workspace, parameters)

    implementation = _CountingImplementation()
    node = _planned_node(implementation)
    cache = ExecutionCache()
    executor = SequentialBatchExecutor()
    market_view = _market_view()
    context = _context()
    plan = ExecutionPlan(nodes=(node,))

    executor.execute(plan, market_view=market_view, context=context, cache=cache)
    executor.execute(plan, market_view=market_view, context=context, cache=cache)
    assert call_count == 1
    assert len(cache) == 1


def test_executor_wraps_implementation_failures() -> None:
    executor = SequentialBatchExecutor()
    with pytest.raises(ImplementationExecutionError, match="adapter failed"):
        executor.execute(
            ExecutionPlan(nodes=(_planned_node(_FailingImplementation()),)),
            market_view=_market_view(),
            context=_context(),
        )


def test_executor_rejects_invalid_output_length() -> None:
    class _ShortOutputImplementation(_ConstantImplementation):
        def compute(
            self,
            context: AnalysisContext,
            workspace: AnalysisWorkspaceView,
            parameters: CanonicalParameters,
        ) -> AnalysisResult:
            result = super().compute(context, workspace, parameters)
            output_id = OutputId("value")
            return AnalysisResult(
                computation_identity=result.computation_identity,
                output_schema=result.output_schema,
                outputs={output_id: OutputSeries(values=(1.0,))},
                lineage=result.lineage,
                validity=result.validity,
                warmup=result.warmup,
                availability=result.availability,
                diagnostics=result.diagnostics,
            )

    executor = SequentialBatchExecutor()
    with pytest.raises(OutputValidationError, match="length"):
        executor.execute(
            ExecutionPlan(nodes=(_planned_node(_ShortOutputImplementation()),)),
            market_view=_market_view(),
            context=_context(),
        )
