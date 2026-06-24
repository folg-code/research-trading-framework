"""Tests for AnalysisFrame assembly."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

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
    TimeRange,
)
from trading_framework.market_analysis.assembly.assembler import AliasCollisionError, default_alias
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_mvp_components
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe


def _bars() -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[MarketBar] = []
    for index, close in enumerate([100.0, 102.0, 101.0, 103.0, 104.0]):
        observed = base.replace(hour=index)
        price = Price(Decimal(str(close)))
        bars.append(
            MarketBar(
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Volume(1000),
                observed_at=observed,
                available_at=observed.replace(minute=1),
            )
        )
    return bars


def _execute_slice() -> tuple[AnalysisContext, AnalysisWorkspace]:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    view = AnalysisDataView.from_bars(_bars())
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    context = AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1h"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )
    state_params = VolatilityStateComponent().parameter_schema.canonicalize(
        {"period": 3, "threshold": 5.0}
    )
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 3})
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=context.dataset_ref,
            timeframe=context.timeframe,
            requested_range=context.requested_range,
        ),
        [
            PlanningRequest.from_component_request(
                ComponentRequest(
                    component_id=ComponentId("volatility.state"),
                    parameters=state_params,
                )
            ),
            PlanningRequest.from_component_request(
                ComponentRequest(
                    component_id=ComponentId("trend.ema"),
                    parameters=ema_params,
                )
            ),
        ],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=context,
    )
    return context, workspace


def test_default_alias_is_deterministic() -> None:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    view = AnalysisDataView.from_bars(_bars())
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    context = AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1h"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )
    period_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=context.dataset_ref,
            timeframe=context.timeframe,
            requested_range=context.requested_range,
        ),
        [
            PlanningRequest.from_component_request(
                ComponentRequest(
                    component_id=ComponentId("volatility.atr"),
                    parameters=period_params,
                )
            )
        ],
    )
    workspace = SequentialBatchExecutor().execute(plan, market_view=view, context=context)
    atr_result = next(
        result
        for result in workspace.result_store.results().values()
        if result.computation_identity.component_id == ComponentId("volatility.atr")
    )
    alias = default_alias(atr_result.computation_identity, OutputId("value"))
    assert alias == "volatility_atr_value_3"


def test_assembler_builds_wide_frame_with_lineage() -> None:
    _, workspace = _execute_slice()
    state_params = VolatilityStateComponent().parameter_schema.canonicalize(
        {"period": 3, "threshold": 5.0}
    )
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 3})
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.true_range"),
                    parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
                    output_id=OutputId("value"),
                    alias="true_range",
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=atr_params,
                    output_id=OutputId("value"),
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("trend.ema"),
                    parameters=ema_params,
                    output_id=OutputId("value"),
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.state"),
                    parameters=state_params,
                    output_id=OutputId("state"),
                ),
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.state"),
                    parameters=state_params,
                    output_id=OutputId("distance_to_threshold"),
                ),
            )
        ),
    )
    assert "close" in frame.columns
    assert "true_range" in frame.columns
    assert "volatility_atr_value_3" in frame.columns
    assert "trend_ema_value_3" in frame.columns
    assert "volatility_state_state_3_5" in frame.columns
    assert "volatility_state_distance_to_threshold_3_5" in frame.columns
    assert frame.column_lineage["true_range"].output_id == OutputId("value")


def test_assembler_detects_alias_collision() -> None:
    _, workspace = _execute_slice()
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    request = AnalysisFrameRequest(
        market_fields=(),
        analysis_columns=(
            AnalysisFrameColumnSpec(
                component_id=ComponentId("volatility.atr"),
                parameters=atr_params,
                output_id=OutputId("value"),
                alias="dup",
            ),
            AnalysisFrameColumnSpec(
                component_id=ComponentId("volatility.true_range"),
                parameters=TrueRangeComponent().parameter_schema.canonicalize({}),
                output_id=OutputId("value"),
                alias="dup",
            ),
        ),
    )
    with pytest.raises(AliasCollisionError):
        AnalysisFrameAssembler().assemble(workspace, request)
