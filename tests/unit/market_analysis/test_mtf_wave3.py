"""Sprint 004 Wave 3 — available_at, alignment and MTF frame assembly tests."""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.temporal.bar_interval import derive_bar_interval
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisFrameAssembler,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
    ComponentId,
    ComponentRequest,
    OutputId,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    PlanningContext,
    PlanningRequest,
    RequestResolver,
    ResampleSpec,
    SequentialBatchExecutor,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    derive_available_at_timestamps,
)
from trading_framework.market_analysis.assembly.alignment_cache import AlignmentCache
from trading_framework.market_analysis.components.trend import EmaComponent, NumpyEmaImplementation
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyTrueRangeImplementation,
    TrueRangeComponent,
)
from trading_framework.market_analysis.data.align import align_values_to_evaluation_grid
from trading_framework.market_analysis.data.resample import resample_analysis_view
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.identity.mtf import AlignmentIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.planning import DependencyPlanner
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
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


def _mtf_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register(TrueRangeComponent(), NumpyTrueRangeImplementation())
    registry.register(AtrComponent(), NumpyAtrImplementation())
    registry.register(EmaComponent(), NumpyEmaImplementation())
    return registry


def _execute_mtf_atr_and_ema() -> tuple[AnalysisContext, AnalysisWorkspace]:
    source_view = _build_1m_fixture()
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=3),))
    atr_request = ComponentRequest.from_raw(
        ComponentId("volatility.atr"),
        schema,
        {"period": 3},
        computation_timeframe=Timeframe("5m"),
    )
    ema_request = ComponentRequest.from_raw(
        ComponentId("trend.ema"),
        schema,
        {"period": 3},
    )
    resolved_plan = RequestResolver.resolve_input_plan(
        dataset_ref=_dataset_ref(),
        requested_range=_time_range(),
        source_timeframe=Timeframe("1m"),
        component_requests=(
            (ComponentId("volatility.atr"), atr_request, None),
            (ComponentId("trend.ema"), ema_request, None),
        ),
        evaluation_timeframe=Timeframe("1m"),
    )
    planning_context = PlanningContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=_time_range(),
        evaluation_timeframe=Timeframe("1m"),
    )
    plan = DependencyPlanner(_mtf_registry()).build_plan(
        planning_context,
        [
            PlanningRequest.from_component_request(atr_request),
            PlanningRequest.from_component_request(ema_request),
        ],
        resolved_plan=resolved_plan,
    )
    context = AnalysisContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=_time_range(),
        computation_range=_time_range(),
        engine_version="0.1.0",
        evaluation_timeframe=Timeframe("1m"),
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=source_view,
        context=context,
    )
    return context, workspace


def test_htf_atr_result_includes_available_at_metadata() -> None:
    _, workspace = _execute_mtf_atr_and_ema()
    atr_result = next(
        result
        for result in workspace.result_store.results().values()
        if result.computation_identity.component_id == ComponentId("volatility.atr")
    )
    series = atr_result.outputs[OutputId("value")]
    assert series.available_at is not None
    assert len(series.available_at) == len(series.values)
    expected_first = derive_bar_interval(_utc(2024, 6, 3, 10, 0), Timeframe("5m"))[1]
    assert series.available_at[0] == expected_first


def test_single_tf_output_omits_available_at() -> None:
    _, workspace = _execute_mtf_atr_and_ema()
    ema_result = next(
        result
        for result in workspace.result_store.results().values()
        if result.computation_identity.component_id == ComponentId("trend.ema")
    )
    assert ema_result.outputs[OutputId("value")].available_at is None


def test_alignment_avoids_lookahead_at_1037() -> None:
    source_view = _build_1m_fixture()
    resampled = resample_analysis_view(source_view, ResampleSpec(target_timeframe=Timeframe("5m")))
    available_at = derive_available_at_timestamps(resampled.timestamps, Timeframe("5m"))
    values = tuple(float(index) for index in range(len(resampled)))
    evaluation_timestamps = source_view.timestamps
    aligned = align_values_to_evaluation_grid(
        values=values,
        available_at=available_at,
        evaluation_timestamps=evaluation_timestamps,
        policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    eval_1037 = _utc(2024, 6, 3, 10, 37)
    index_1037 = evaluation_timestamps.index(eval_1037)
    joined_value = aligned[index_1037]
    assert joined_value == 6.0
    incomplete_bar_available = _utc(2024, 6, 3, 10, 40)
    assert available_at[7] == incomplete_bar_available
    assert joined_value != 8.0


def test_alignment_leaves_warmup_gaps_as_nan() -> None:
    source_view = _build_1m_fixture()
    resampled = resample_analysis_view(source_view, ResampleSpec(target_timeframe=Timeframe("5m")))
    available_at = derive_available_at_timestamps(resampled.timestamps, Timeframe("5m"))
    values = tuple(float("nan") if index < 2 else float(index) for index in range(len(resampled)))
    aligned = align_values_to_evaluation_grid(
        values=values,
        available_at=available_at,
        evaluation_timestamps=source_view.timestamps[:10],
        policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    assert all(math.isnan(value) for value in aligned[:5])


def test_alignment_cache_is_keyed_by_alignment_identity() -> None:
    cache = AlignmentCache()
    identity = AlignmentIdentity(
        component_computation_key='{"kind":"component_computation"}',
        output_id="value",
        evaluation_timeframe=Timeframe("1m"),
        evaluation_range=_time_range(),
        alignment_policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    cache.put(identity, (1.0, 2.0))
    assert cache.get(identity) == (1.0, 2.0)


def test_frame_assembler_aligns_mixed_timeframes() -> None:
    context, workspace = _execute_mtf_atr_and_ema()
    schema = ParameterSchema(fields=(ParameterFieldSpec("period", ParameterType.INT, default=3),))
    atr_params = schema.canonicalize({"period": 3})
    ema_params = schema.canonicalize({"period": 3})
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            market_fields=("close",),
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=atr_params,
                    output_id=OutputId("value"),
                    alias="atr_5m",
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("trend.ema"),
                    parameters=ema_params,
                    output_id=OutputId("value"),
                    alias="ema_1m",
                ),
            ),
        ),
        evaluation_timeframe=context.evaluation_timeframe,
        evaluation_range=context.requested_range,
    )
    assert len(frame.timestamps) == 45
    assert len(frame.columns["close"]) == 45
    assert len(frame.columns["atr_5m"]) == 45
    assert len(frame.columns["ema_1m"]) == 45
    assert not math.isnan(frame.columns["ema_1m"][3])
    assert math.isnan(frame.columns["atr_5m"][0])
