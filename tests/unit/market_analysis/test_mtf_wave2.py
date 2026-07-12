"""Sprint 004 Wave 2 — resampling, resolution plan, and DAG integration tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl

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
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    PlannedNode,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
    ResampleCache,
    ResampleNode,
    ResampleSpec,
    SequentialBatchExecutor,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.data.resample import (
    analysis_view_to_polars,
    resample_analysis_view,
    resample_ohlcv_dataframe,
    verify_source_frame_unchanged,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution.warmup import max_history_requirement
from trading_framework.market_analysis.planning import DependencyPlanner
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView
from trading_framework.time.models.timeframe import Timeframe


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )


def _time_range() -> TimeRange:
    return TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )


def _build_1m_fixture() -> AnalysisDataView:
    start = _utc(2024, 6, 3, 10, 0)
    bars: list[MarketBar] = []
    price = 100.0
    for index in range(45):
        observed_at = start + timedelta(minutes=index)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(price))),
                high=Price(Decimal(str(price + 1.0))),
                low=Price(Decimal(str(price - 0.5))),
                close=Price(Decimal(str(price + 0.25))),
                volume=Volume(1_000 + index),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
        price += 0.1
    return AnalysisDataView.from_bars(bars)


class _CloseCopyComponent:
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


class _CloseCopyImplementation:
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
            computation_timeframe=context.timeframe,
            requested_range=context.requested_range,
            dependency_keys=(),
            input_identity_key=None,
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


def _registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register(_CloseCopyComponent(), _CloseCopyImplementation())
    return registry


def _planning_context() -> PlanningContext:
    return PlanningContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=_time_range(),
    )


def test_resample_ohlcv_matches_spike_rules() -> None:
    source_view = _build_1m_fixture()
    source_frame = analysis_view_to_polars(source_view)
    spec = ResampleSpec(target_timeframe=Timeframe("5m"))
    resampled = resample_ohlcv_dataframe(source_frame, spec)
    bucket = source_frame.filter(
        (pl.col("observed_at") >= _utc(2024, 6, 3, 10, 0))
        & (pl.col("observed_at") < _utc(2024, 6, 3, 10, 5))
    )
    row = resampled.filter(resampled["observed_at"] == _utc(2024, 6, 3, 10, 0)).row(0, named=True)
    assert row["open"] == bucket["open"][0]
    assert row["high"] == bucket["high"].max()
    assert row["low"] == bucket["low"].min()
    assert row["close"] == bucket["close"][-1]
    assert row["volume"] == bucket["volume"].sum()


def test_resample_does_not_mutate_source_frame() -> None:
    source_view = _build_1m_fixture()
    before = analysis_view_to_polars(source_view)
    snapshot = before.clone()
    spec = ResampleSpec(target_timeframe=Timeframe("5m"))
    _ = resample_ohlcv_dataframe(before, spec)
    assert verify_source_frame_unchanged(snapshot, before)


def test_resample_analysis_view_produces_coarser_bar_count() -> None:
    source_view = _build_1m_fixture()
    resampled = resample_analysis_view(source_view, ResampleSpec(target_timeframe=Timeframe("5m")))
    assert len(resampled) == 9
    assert len(source_view) == 45


def test_resolve_input_plan_adds_resample_when_computation_is_coarser() -> None:
    schema = ParameterSchema(fields=())
    request = ComponentRequest.from_raw(
        ComponentId("price.close_copy"),
        schema,
        {},
        computation_timeframe=Timeframe("5m"),
    )
    plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=_time_range(),
        source_timeframe=Timeframe("1m"),
        component_requests=((ComponentId("price.close_copy"), request, None),),
    )
    assert len(plan.components) == 1
    component = plan.components[0]
    assert component.resample_requirement is not None
    assert component.resolved.input_identity_key is not None
    assert component.resample_requirement.resample_spec.target_timeframe == Timeframe("5m")


def test_resolve_input_plan_skips_resample_for_source_timeframe() -> None:
    schema = ParameterSchema(fields=())
    request = ComponentRequest.from_raw(ComponentId("price.close_copy"), schema, {})
    plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=_time_range(),
        source_timeframe=Timeframe("1m"),
        component_requests=((ComponentId("price.close_copy"), request, None),),
    )
    assert plan.components[0].resample_requirement is None
    assert plan.components[0].resolved.input_identity_key is None


def test_planner_inserts_deduplicated_resample_nodes() -> None:
    schema = ParameterSchema(fields=())
    atr_request = ComponentRequest.from_raw(
        ComponentId("price.close_copy"),
        schema,
        {},
        computation_timeframe=Timeframe("5m"),
    )
    ema_request = ComponentRequest.from_raw(
        ComponentId("price.close_copy"),
        schema,
        {},
        computation_timeframe=Timeframe("5m"),
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=_time_range(),
        source_timeframe=Timeframe("1m"),
        component_requests=(
            (ComponentId("price.close_copy"), atr_request, None),
            (ComponentId("price.close_copy"), ema_request, None),
        ),
    )
    planner = DependencyPlanner(_registry())
    plan = planner.build_plan(
        _planning_context(),
        [
            PlanningRequest.from_component_request(atr_request),
            PlanningRequest.from_component_request(ema_request),
        ],
        resolved_plan=resolved_plan,
    )
    assert len(plan.resample_nodes()) == 1
    assert len(plan.component_nodes()) == 1
    assert isinstance(plan.nodes[0], ResampleNode)
    component_node = plan.component_nodes()[0]
    assert component_node.computation_identity.input_identity_key == plan.resample_keys()[0]


def test_executor_runs_resample_once_for_shared_target_timeframe() -> None:
    source_view = _build_1m_fixture()
    schema = ParameterSchema(fields=())
    request = ComponentRequest.from_raw(
        ComponentId("price.close_copy"),
        schema,
        {},
        computation_timeframe=Timeframe("5m"),
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=_time_range(),
        source_timeframe=Timeframe("1m"),
        component_requests=((ComponentId("price.close_copy"), request, None),),
    )
    planner = DependencyPlanner(_registry())
    plan = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
        resolved_plan=resolved_plan,
    )
    resample_cache = ResampleCache()
    context = AnalysisContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=_time_range(),
        computation_range=_time_range(),
        engine_version="0.1.0",
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=source_view,
        context=context,
        resample_cache=resample_cache,
    )
    assert len(resample_cache) == 1
    assert len(workspace.market_view) == 45
    stored_results = workspace.result_store.results()
    assert len(stored_results) == 1
    result = next(iter(stored_results.values()))
    assert result.outputs[OutputId("value")].length == 9


class _WarmComponent(_CloseCopyComponent):
    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=14)


def test_max_history_requirement_scales_warmup_to_source_bars() -> None:
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),))
    request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 14},
        computation_timeframe=Timeframe("5m"),
    )
    node = PlannedNode(
        request=request,
        component=_WarmComponent(),
        implementation=_CloseCopyImplementation(),
        computation_identity=ComputationIdentity(
            component_id=ComponentId("volatility.atr"),
            component_version=ComponentVersion("1.0.0"),
            implementation_id=ImplementationId("numpy.atr"),
            implementation_version=ImplementationVersion("1.0.0"),
            parameters=schema.canonicalize({"period": 14}),
            dataset_ref=_dataset_ref(),
            computation_timeframe=Timeframe("5m"),
            requested_range=_time_range(),
            dependency_keys=(),
        ),
        dependency_keys=(),
    )
    warmup = max_history_requirement(
        ExecutionPlan(nodes=(node,)),
        source_timeframe=Timeframe("1m"),
    )
    assert warmup == 70
