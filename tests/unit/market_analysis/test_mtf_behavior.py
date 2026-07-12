"""Sprint 004 T012 — behavior-focused MTF regression suite.

Covers the seven required behavioral areas from SPRINT_004 Design Principles.
Tests assert outputs and timestamps, not internal DAG node types.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl

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
    PlanningContext,
    PlanningRequest,
    RequestResolver,
    ResampleCache,
    ResampleSpec,
    SequentialBatchExecutor,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    derive_available_at_timestamps,
)
from trading_framework.market_analysis.components.trend import EmaComponent, NumpyEmaImplementation
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyTrueRangeImplementation,
    TrueRangeComponent,
)
from trading_framework.market_analysis.data.align import align_values_to_evaluation_grid
from trading_framework.market_analysis.data.resample import (
    analysis_view_to_polars,
    resample_analysis_view,
    resample_ohlcv_dataframe,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.identity.mtf import ResampleIdentity
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.planning import DependencyPlanner
from trading_framework.market_analysis.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import (
    AnalysisWorkspace,
    AnalysisWorkspaceView,
)
from trading_framework.time.models.timeframe import Timeframe


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def _dataset_ref(*, version: int = 1) -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=version,
    )


def _time_range() -> TimeRange:
    return TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )


def _build_1m_fixture(*, bar_count: int = 45) -> AnalysisDataView:
    start = _utc(2024, 6, 3, 10, 0)
    bars: list[MarketBar] = []
    price = 100.0
    for index in range(bar_count):
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


def _build_1m_polars(*, start: datetime, bar_count: int) -> pl.DataFrame:
    rows: list[dict[str, float | datetime]] = []
    price = 100.0
    for index in range(bar_count):
        observed_at = start + timedelta(minutes=index)
        rows.append(
            {
                "observed_at": observed_at,
                "open": price,
                "high": price + 1.0,
                "low": price - 0.5,
                "close": price + 0.25,
                "volume": float(1_000 + index),
            }
        )
        price += 0.1
    return pl.DataFrame(rows).sort("observed_at")


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
            input_identity_key=workspace.input_identity_key,
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


def _dedupe_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register(_CloseCopyComponent(), _CloseCopyImplementation())
    return registry


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


def test_behavior_resampling_ohlcv_correctness() -> None:
    source_frame = analysis_view_to_polars(_build_1m_fixture())
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


def test_behavior_no_lookahead_on_evaluation_grid() -> None:
    source_view = _build_1m_fixture()
    resampled = resample_analysis_view(source_view, ResampleSpec(target_timeframe=Timeframe("5m")))
    available_at = derive_available_at_timestamps(resampled.timestamps, Timeframe("5m"))
    values = tuple(float(index) for index in range(len(resampled)))
    aligned = align_values_to_evaluation_grid(
        values=values,
        available_at=available_at,
        evaluation_timestamps=source_view.timestamps,
        policy=AlignmentPolicy.LAST_CLOSED_BAR,
    )
    eval_1037 = _utc(2024, 6, 3, 10, 37)
    index_1037 = source_view.timestamps.index(eval_1037)
    joined_value = aligned[index_1037]
    incomplete_bar_available = _utc(2024, 6, 3, 10, 40)
    assert available_at[7] == incomplete_bar_available
    assert joined_value == 6.0
    assert joined_value != 8.0


def test_behavior_shared_resample_executed_once() -> None:
    source_view = _build_1m_fixture()
    schema = ParameterSchema(fields=())
    first_request = ComponentRequest.from_raw(
        ComponentId("price.close_copy"),
        schema,
        {},
        computation_timeframe=Timeframe("5m"),
    )
    second_request = ComponentRequest.from_raw(
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
            (ComponentId("price.close_copy"), first_request, None),
            (ComponentId("price.close_copy"), second_request, None),
        ),
    )
    plan = DependencyPlanner(_dedupe_registry()).build_plan(
        PlanningContext(
            dataset_ref=_dataset_ref(),
            timeframe=Timeframe("1m"),
            requested_range=_time_range(),
        ),
        [
            PlanningRequest.from_component_request(first_request),
            PlanningRequest.from_component_request(second_request),
        ],
        resolved_plan=resolved_plan,
    )
    resample_cache = ResampleCache()
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=source_view,
        context=AnalysisContext(
            dataset_ref=_dataset_ref(),
            timeframe=Timeframe("1m"),
            requested_range=_time_range(),
            computation_range=_time_range(),
            engine_version="0.1.0",
        ),
        resample_cache=resample_cache,
    )
    assert len(resample_cache) == 1
    stored_results = workspace.result_store.results()
    assert len(stored_results) == 1


def test_behavior_material_input_change_changes_identity_layer() -> None:
    time_range = _time_range()
    baseline = ResampleIdentity(
        dataset_ref=_dataset_ref(version=1),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("5m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("5m")),
        requested_range=time_range,
    )
    new_dataset_version = ResampleIdentity(
        dataset_ref=_dataset_ref(version=2),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("5m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("5m")),
        requested_range=time_range,
    )
    coarser_target = ResampleIdentity(
        dataset_ref=_dataset_ref(version=1),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("15m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("15m")),
        requested_range=time_range,
    )
    duplicate = ResampleIdentity(
        dataset_ref=_dataset_ref(version=1),
        source_timeframe=Timeframe("1m"),
        target_timeframe=Timeframe("5m"),
        resample_spec=ResampleSpec(target_timeframe=Timeframe("5m")),
        requested_range=time_range,
    )
    assert baseline.canonical_key() == duplicate.canonical_key()
    assert baseline.canonical_key() != new_dataset_version.canonical_key()
    assert baseline.canonical_key() != coarser_target.canonical_key()


def test_behavior_end_to_end_mtf_frame_correctness() -> None:
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


def test_behavior_partial_bucket_edge() -> None:
    spec = ResampleSpec(target_timeframe=Timeframe("5m"))
    leading_partial = _build_1m_polars(start=_utc(2024, 1, 2, 14, 32), bar_count=8)
    leading_resampled = resample_ohlcv_dataframe(leading_partial, spec)
    first_bucket = leading_resampled.filter(
        leading_resampled["observed_at"] == _utc(2024, 1, 2, 14, 30)
    ).row(0, named=True)
    leading_slice = leading_partial.filter(
        (pl.col("observed_at") >= _utc(2024, 1, 2, 14, 32))
        & (pl.col("observed_at") < _utc(2024, 1, 2, 14, 35))
    )
    assert first_bucket["open"] == leading_slice["open"][0]
    assert first_bucket["close"] == leading_slice["close"][-1]
    assert leading_resampled.height == 2

    trailing_partial = _build_1m_polars(start=_utc(2024, 1, 2, 14, 30), bar_count=12)
    trailing_resampled = resample_ohlcv_dataframe(trailing_partial, spec)
    last_bucket = trailing_resampled.filter(
        trailing_resampled["observed_at"] == _utc(2024, 1, 2, 14, 40)
    ).row(0, named=True)
    trailing_slice = trailing_partial.filter(
        (pl.col("observed_at") >= _utc(2024, 1, 2, 14, 40))
        & (pl.col("observed_at") < _utc(2024, 1, 2, 14, 45))
    )
    assert last_bucket["open"] == trailing_slice["open"][0]
    assert last_bucket["close"] == trailing_slice["close"][-1]
    assert trailing_resampled.height == 3


def test_behavior_warmup_missing_htf_history() -> None:
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
    first_available = derive_bar_interval(_utc(2024, 6, 3, 10, 0), Timeframe("5m"))[1]
    assert available_at[0] == first_available
