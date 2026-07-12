"""Sprint 005 Wave 3 — MTF swing event vs state alignment tests."""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisFrameAssembler,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
    ComponentId,
    ComponentRequest,
    OutputId,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    derive_available_at_timestamps,
)
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.data.align import (
    align_event_at_available,
    align_values_to_evaluation_grid,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.identity.mtf import AlignmentIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.planning import DependencyPlanner
from trading_framework.market_analysis.registry.builtins import register_swing_structure_component
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="test",
        ),
        version=1,
    )


def _time_range(start: datetime, end: datetime) -> TimeRange:
    return TimeRange(start=start, end=end)


def _build_swing_1m_fixture() -> AnalysisDataView:
    """1m bars engineered so 5m resampled highs form clear swing-high candidates."""
    start = _utc(2024, 6, 3, 10, 0)
    target_5m_highs = [10.0, 25.0, 18.0, 30.0, 22.0, 35.0, 28.0, 40.0]
    bars: list[MarketBar] = []
    minute = 0
    for target_high in target_5m_highs:
        for offset in range(5):
            observed_at = start + timedelta(minutes=minute)
            high = target_high if offset == 2 else target_high - 3.0
            low = high - 1.0
            bars.append(
                MarketBar(
                    open=Price(Decimal(str(high - 0.5))),
                    high=Price(Decimal(str(high))),
                    low=Price(Decimal(str(low))),
                    close=Price(Decimal(str(high - 0.25))),
                    volume=Volume(1_000 + minute),
                    observed_at=observed_at,
                    available_at=observed_at + timedelta(minutes=1),
                )
            )
            minute += 1
    return AnalysisDataView.from_bars(bars)


def _target_high_for_pivot15_bucket(bucket: int) -> float:
    if bucket < 15:
        return 50.0 + bucket
    if bucket == 15:
        return 100.0
    if bucket <= 30:
        return 100.0 - (bucket - 15)
    return 60.0 + (bucket % 5)


def _build_long_swing_1m_fixture(*, bucket_count: int = 50) -> AnalysisDataView:
    """Enough 5m buckets for pivot_range=15 on the HTF computation grid."""
    start = _utc(2024, 6, 3, 10, 0)
    bars: list[MarketBar] = []
    minute = 0
    for bucket in range(bucket_count):
        target_high = _target_high_for_pivot15_bucket(bucket)
        for offset in range(5):
            observed_at = start + timedelta(minutes=minute)
            high = target_high if offset == 2 else target_high - 3.0
            low = high - 1.0
            bars.append(
                MarketBar(
                    open=Price(Decimal(str(high - 0.5))),
                    high=Price(Decimal(str(high))),
                    low=Price(Decimal(str(low))),
                    close=Price(Decimal(str(high - 0.25))),
                    volume=Volume(1_000 + minute),
                    observed_at=observed_at,
                    available_at=observed_at + timedelta(minutes=1),
                )
            )
            minute += 1
    return AnalysisDataView.from_bars(bars)


def _execute_mtf_swing_from_view(
    source_view: AnalysisDataView,
    *,
    pivot_range: int,
) -> tuple[AnalysisContext, AnalysisWorkspace]:
    swing_schema = SwingStructureComponent().parameter_schema
    swing_request = ComponentRequest.from_raw(
        ComponentId("structure.swing"),
        swing_schema,
        {"pivot_range": pivot_range},
        computation_timeframe=Timeframe("5m"),
    )
    time_range = _time_range(source_view.timestamps[0], source_view.timestamps[-1])
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=time_range,
        source_timeframe=Timeframe("1m"),
        component_requests=((ComponentId("structure.swing"), swing_request, None),),
        evaluation_timeframe=Timeframe("1m"),
    )
    registry = ComponentRegistry()
    register_swing_structure_component(registry)
    plan = DependencyPlanner(registry).build_plan(
        PlanningContext(
            dataset_ref=_dataset_ref(),
            timeframe=Timeframe("1m"),
            requested_range=time_range,
            evaluation_timeframe=Timeframe("1m"),
        ),
        [PlanningRequest.from_component_request(swing_request)],
        resolved_plan=resolved_plan,
    )
    context = AnalysisContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=time_range,
        computation_range=time_range,
        engine_version="0.1.0",
        evaluation_timeframe=Timeframe("1m"),
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=source_view,
        context=context,
    )
    return context, workspace


def _execute_mtf_swing(*, pivot_range: int = 1) -> tuple[AnalysisContext, AnalysisWorkspace]:
    return _execute_mtf_swing_from_view(_build_swing_1m_fixture(), pivot_range=pivot_range)


def test_event_at_available_projects_single_bar_not_forward_filled() -> None:
    evaluation_timestamps = tuple(_utc(2024, 6, 3, 10, minute) for minute in range(0, 15))
    available_at = (
        _utc(2024, 6, 3, 10, 5),
        _utc(2024, 6, 3, 10, 10),
        _utc(2024, 6, 3, 10, 15),
    )
    values = (0.0, 1.0, 0.0)
    aligned = align_event_at_available(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
    )
    assert aligned[evaluation_timestamps.index(_utc(2024, 6, 3, 10, 9))] == 0.0
    assert aligned[evaluation_timestamps.index(_utc(2024, 6, 3, 10, 10))] == 1.0
    assert aligned[evaluation_timestamps.index(_utc(2024, 6, 3, 10, 11))] == 0.0


def test_last_closed_bar_would_forward_fill_event_flags() -> None:
    evaluation_timestamps = tuple(_utc(2024, 6, 3, 10, minute) for minute in range(0, 15))
    available_at = (
        _utc(2024, 6, 3, 10, 5),
        _utc(2024, 6, 3, 10, 10),
        _utc(2024, 6, 3, 10, 15),
    )
    values = (0.0, 1.0, 0.0)
    last_closed = align_values_to_evaluation_grid(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    event_at_available = align_event_at_available(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
    )
    assert sum(value == 1.0 for value in last_closed) > sum(
        value == 1.0 for value in event_at_available
    )


def test_alignment_identity_includes_output_id_for_cache_isolation() -> None:
    computation_key = '{"kind":"component_computation"}'
    time_range = _time_range(_utc(2024, 1, 1, 0, 0), _utc(2024, 1, 2, 0, 0))
    event_identity = AlignmentIdentity(
        component_computation_key=computation_key,
        output_id="swing_high_event",
        evaluation_timeframe=Timeframe("1m"),
        evaluation_range=time_range,
        alignment_policy=AlignmentPolicy.EVENT_AT_AVAILABLE,
    )
    state_identity = AlignmentIdentity(
        component_computation_key=computation_key,
        output_id="latest_swing_high_level",
        evaluation_timeframe=Timeframe("1m"),
        evaluation_range=time_range,
        alignment_policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    assert event_identity.canonical_key() != state_identity.canonical_key()


def test_swing_schema_declares_per_output_alignment_policies() -> None:
    schema = SwingStructureComponent().output_schema
    policies = {field.output_id.value: field.alignment_policy for field in schema.outputs}
    assert policies["swing_high_event"] is AlignmentPolicy.EVENT_AT_AVAILABLE
    assert policies["latest_swing_high_level"] is AlignmentPolicy.LAST_CLOSED_BAR


def test_mtf_swing_frame_aligns_events_without_forward_fill() -> None:
    context, workspace = _execute_mtf_swing(pivot_range=1)
    swing_result = next(iter(workspace.result_store.results().values()))
    htf_events = swing_result.outputs[OutputId("swing_high_event")]
    assert htf_events.available_at is not None
    htf_event_count = sum(value == 1.0 for value in htf_events.values)
    assert htf_event_count > 0

    parameters = SwingStructureComponent().parameter_schema.canonicalize({"pivot_range": 1})
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            market_fields=(),
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("structure.swing"),
                    parameters=parameters,
                    output_id=OutputId("swing_high_event"),
                    alias="swing_high_event_5m",
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("structure.swing"),
                    parameters=parameters,
                    output_id=OutputId("latest_swing_high_level"),
                    alias="latest_swing_high_level_5m",
                ),
            ),
        ),
        evaluation_timeframe=context.evaluation_timeframe,
        evaluation_range=context.requested_range,
    )
    ltf_events = frame.columns["swing_high_event_5m"]
    assert sum(value == 1.0 for value in ltf_events) == htf_event_count

    state_values = frame.columns["latest_swing_high_level_5m"]
    first_known = next(index for index, value in enumerate(state_values) if not math.isnan(value))
    assert first_known >= 0
    if first_known + 1 < len(state_values):
        assert state_values[first_known + 1] == state_values[first_known]


def test_mtf_swing_state_outputs_include_available_at() -> None:
    _, workspace = _execute_mtf_swing(pivot_range=1)
    swing_result = next(iter(workspace.result_store.results().values()))
    state = swing_result.outputs[OutputId("latest_swing_high_level")]
    assert state.available_at is not None
    assert len(state.available_at) == len(state.values)
    input_key = swing_result.computation_identity.input_identity_key
    htf_view = workspace.market_view_for(input_key)
    expected = derive_available_at_timestamps(htf_view.timestamps, Timeframe("5m"))
    assert state.available_at == expected


def test_mtf_swing_pivot_range_15_aligns_events_on_long_fixture() -> None:
    pivot_range = 15
    source_view = _build_long_swing_1m_fixture(bucket_count=50)
    context, workspace = _execute_mtf_swing_from_view(source_view, pivot_range=pivot_range)
    swing_result = next(iter(workspace.result_store.results().values()))
    assert swing_result.availability.delay_bars == pivot_range
    assert swing_result.warmup.warmup_bars == pivot_range

    htf_events = swing_result.outputs[OutputId("swing_high_event")]
    htf_event_count = sum(value == 1.0 for value in htf_events.values)
    assert htf_event_count >= 1

    parameters = SwingStructureComponent().parameter_schema.canonicalize(
        {"pivot_range": pivot_range}
    )
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            market_fields=(),
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("structure.swing"),
                    parameters=parameters,
                    output_id=OutputId("swing_high_event"),
                    alias="swing_high_event_5m",
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("structure.swing"),
                    parameters=parameters,
                    output_id=OutputId("latest_swing_high_level"),
                    alias="latest_swing_high_level_5m",
                ),
            ),
        ),
        evaluation_timeframe=context.evaluation_timeframe,
        evaluation_range=context.requested_range,
    )
    ltf_events = frame.columns["swing_high_event_5m"]
    ltf_event_count = sum(value == 1.0 for value in ltf_events)
    assert ltf_event_count >= 1
    assert abs(ltf_event_count - htf_event_count) <= 1
    for index in range(1, len(ltf_events)):
        if ltf_events[index] == 1.0:
            assert ltf_events[index - 1] != 1.0
