"""Workspace and frame assembly regression tests (workspace doc section 31)."""

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
from trading_framework.market_analysis.assembly.assembler import AliasCollisionError
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
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


def _context() -> AnalysisContext:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    return AnalysisContext(
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


def _execute_state_and_ema() -> tuple[AnalysisContext, AnalysisWorkspace]:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    market_view = AnalysisDataView.from_bars(_bars())
    original_open = market_view.open.values
    state_params = VolatilityStateComponent().parameter_schema.canonicalize(
        {"period": 3, "threshold": 5.0}
    )
    ema_params = EmaComponent().parameter_schema.canonicalize({"period": 3})
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=_context().dataset_ref,
            timeframe=Timeframe("1h"),
            requested_range=_context().requested_range,
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
        market_view=market_view,
        context=_context(),
    )
    assert market_view.open.values == original_open
    return _context(), workspace


def test_workspace_reuses_shared_atr_for_state_chain() -> None:
    _, workspace = _execute_state_and_ema()
    component_ids = {
        result.computation_identity.component_id
        for result in workspace.result_store.results().values()
    }
    assert ComponentId("volatility.true_range") in component_ids
    assert ComponentId("volatility.atr") in component_ids
    assert ComponentId("volatility.state") in component_ids
    assert ComponentId("trend.ema") in component_ids
    assert len(workspace.result_store) == 4


def test_frame_assembler_selects_requested_outputs_only() -> None:
    _, workspace = _execute_state_and_ema()
    state_params = VolatilityStateComponent().parameter_schema.canonicalize(
        {"period": 3, "threshold": 5.0}
    )
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            market_fields=("close",),
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.state"),
                    parameters=state_params,
                    output_id=OutputId("state"),
                    alias="vol_state",
                ),
            ),
        ),
    )
    assert set(frame.columns) == {"close", "vol_state"}
    assert frame.column_lineage["vol_state"].computation_identity.component_id == ComponentId(
        "volatility.state"
    )


def test_frame_assembler_injects_dependency_output_by_ref() -> None:
    _, workspace = _execute_state_and_ema()
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(
            analysis_columns=(
                AnalysisFrameColumnSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=atr_params,
                    output_id=OutputId("value"),
                    alias="atr",
                ),
            )
        ),
    )
    atr_lineage = frame.column_lineage["atr"]
    assert atr_lineage.computation_identity.component_id == ComponentId("volatility.atr")
    assert atr_lineage.output_id == OutputId("value")


def test_frame_assembler_rejects_undetected_alias_collision() -> None:
    _, workspace = _execute_state_and_ema()
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    request = AnalysisFrameRequest(
        analysis_columns=(
            AnalysisFrameColumnSpec(
                component_id=ComponentId("volatility.atr"),
                parameters=atr_params,
                output_id=OutputId("value"),
                alias="collision",
            ),
            AnalysisFrameColumnSpec(
                component_id=ComponentId("trend.ema"),
                parameters=EmaComponent().parameter_schema.canonicalize({"period": 3}),
                output_id=OutputId("value"),
                alias="collision",
            ),
        )
    )
    with pytest.raises(AliasCollisionError, match="collision"):
        AnalysisFrameAssembler().assemble(workspace, request)
