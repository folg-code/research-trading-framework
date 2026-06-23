"""Dependency planner tests."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisResult,
    CanonicalParameters,
    Causality,
    ComponentDependency,
    ComponentId,
    ComponentKind,
    ComponentOutputRef,
    ComponentRequest,
    ComponentVersion,
    DataFieldDependency,
    HistoryRequirement,
    ImplementationId,
    ImplementationVersion,
    OutputFieldSpec,
    OutputId,
    OutputSchema,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
)
from trading_framework.market_analysis.planning import (
    CyclicDependencyError,
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView
from trading_framework.time.models.timeframe import Timeframe


def _period_schema(default: int = 14) -> ParameterSchema:
    return ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=default),)
    )


def _period_params(period: int) -> CanonicalParameters:
    return _period_schema(period).canonicalize({"period": period})


class _TrueRangeComponent:
    component_id = ComponentId("volatility.true_range")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=1)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return (
            DataFieldDependency("high"),
            DataFieldDependency("low"),
            DataFieldDependency("close"),
        )

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return ()


class _TrueRangeImpl:
    implementation_id = ImplementationId("numpy.true_range")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


class _AtrComponent:
    component_id = ComponentId("volatility.atr")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = _period_schema()
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=int(parameters.get("period")))

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=ComponentId("volatility.true_range"),
                    parameters=_period_schema(period).canonicalize({}),
                    output_id=OutputId("value"),
                )
            ),
        )


class _AtrImpl:
    implementation_id = ImplementationId("numpy.atr")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


class _VolatilityStateComponent:
    component_id = ComponentId("volatility.state")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.STATE
    causality = Causality.CAUSAL
    parameter_schema = _period_schema()
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "str"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=int(parameters.get("period")))

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=ComponentId("volatility.atr"),
                    parameters=_period_params(period),
                    output_id=OutputId("value"),
                )
            ),
        )


class _VolatilityStateImpl:
    implementation_id = ImplementationId("numpy.volatility_state")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


class _CyclicA:
    component_id = ComponentId("cycle.a")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=ComponentId("cycle.b"),
                    parameters=ParameterSchema(fields=()).canonicalize({}),
                    output_id=OutputId("value"),
                )
            ),
        )


class _CyclicAImpl:
    implementation_id = ImplementationId("numpy.cycle_a")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


class _CyclicB:
    component_id = ComponentId("cycle.b")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=ComponentId("cycle.a"),
                    parameters=ParameterSchema(fields=()).canonicalize({}),
                    output_id=OutputId("value"),
                )
            ),
        )


class _CyclicBImpl:
    implementation_id = ImplementationId("numpy.cycle_b")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError


def _registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register(_TrueRangeComponent(), _TrueRangeImpl())
    registry.register(_AtrComponent(), _AtrImpl())
    registry.register(_VolatilityStateComponent(), _VolatilityStateImpl())
    return registry


def _planning_context() -> PlanningContext:
    return PlanningContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="sample",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
    )


def test_planner_expands_nested_dependencies() -> None:
    planner = DependencyPlanner(_registry())
    request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=_period_params(14),
    )
    plan = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    component_ids = [node.request.component_id for node in plan.nodes]
    assert component_ids == [
        ComponentId("volatility.true_range"),
        ComponentId("volatility.atr"),
        ComponentId("volatility.state"),
    ]


def test_planner_order_is_deterministic() -> None:
    planner = DependencyPlanner(_registry())
    request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=_period_params(14),
    )
    first = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    second = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    assert first.computation_keys() == second.computation_keys()


def test_planner_deduplicates_shared_dependency() -> None:
    planner = DependencyPlanner(_registry())
    atr_request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=_period_params(14),
    )
    state_request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=_period_params(14),
    )
    plan = planner.build_plan(
        _planning_context(),
        [
            PlanningRequest.from_component_request(atr_request),
            PlanningRequest.from_component_request(state_request),
        ],
    )
    atr_nodes = [
        node for node in plan.nodes if node.request.component_id == ComponentId("volatility.atr")
    ]
    assert len(atr_nodes) == 1
    assert len(plan.nodes) == 3


def test_planner_detects_cycles() -> None:
    registry = ComponentRegistry()
    registry.register(_CyclicA(), _CyclicAImpl())
    registry.register(_CyclicB(), _CyclicBImpl())
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("cycle.a"),
        parameters=ParameterSchema(fields=()).canonicalize({}),
    )
    with pytest.raises(CyclicDependencyError) as exc_info:
        planner.build_plan(
            _planning_context(),
            [PlanningRequest.from_component_request(request)],
        )
    assert "cycle.a" in exc_info.value.cycle[0]
