"""Tests for volatility feature and state components."""

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    ComponentId,
    ComponentRequest,
    OutputGroup,
    OutputId,
    TimeRange,
)
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
from trading_framework.market_analysis.registry.builtins import register_volatility_components
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe


def _bars() -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    specs = [
        (100, 105, 95, 102, 1000),
        (102, 108, 101, 107, 1100),
        (107, 110, 104, 105, 1200),
        (105, 106, 100, 101, 900),
        (101, 103, 99, 102, 1000),
    ]
    bars: list[MarketBar] = []
    for index, (open_, high, low, close, volume) in enumerate(specs):
        observed = base.replace(hour=index)
        available = observed.replace(hour=index, minute=1)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(volume),
                observed_at=observed,
                available_at=available,
            )
        )
    return bars


def _context(bar_count: int) -> AnalysisContext:
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


def _planning_context() -> PlanningContext:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    return PlanningContext(
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
    )


def test_true_range_component_declares_history_and_data_dependencies() -> None:
    component = TrueRangeComponent()
    parameters = component.parameter_schema.canonicalize({})
    assert component.history_requirement(parameters).bars_before == 1
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"high", "low", "close"}


def test_atr_component_depends_on_true_range_output() -> None:
    component = AtrComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14})
    dependencies = component.component_dependencies(parameters)
    assert len(dependencies) == 1
    assert dependencies[0].output_ref.component_id == ComponentId("volatility.true_range")
    assert dependencies[0].output_ref.output_id == OutputId("value")


def test_volatility_state_exposes_core_and_diagnostic_outputs() -> None:
    component = VolatilityStateComponent()
    output_groups = {field.output_id: field.group for field in component.output_schema.outputs}
    assert output_groups[OutputId("state")] == OutputGroup.CORE
    assert output_groups[OutputId("distance_to_threshold")] == OutputGroup.DIAGNOSTIC


def test_executor_runs_true_range_then_atr() -> None:
    registry = ComponentRegistry()
    register_volatility_components(registry)
    view = AnalysisDataView.from_bars(_bars())
    context = _context(len(view))
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=AtrComponent().parameter_schema.canonicalize({"period": 3}),
    )
    plan = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=context,
    )
    assert len(workspace.result_store) == 2
    atr_key = next(
        key
        for key, result in workspace.result_store.results().items()
        if result.computation_identity.component_id == ComponentId("volatility.atr")
    )
    atr_result = workspace.result_store.results()[atr_key]
    atr_values = atr_result.outputs[OutputId("value")].values
    assert np.isnan(atr_values[0])
    assert np.isnan(atr_values[1])
    assert atr_values[2] == pytest.approx((10.0 + 7.0 + 6.0) / 3.0)


def test_executor_runs_volatility_state_chain() -> None:
    registry = ComponentRegistry()
    register_volatility_components(registry)
    view = AnalysisDataView.from_bars(_bars())
    context = _context(len(view))
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=VolatilityStateComponent().parameter_schema.canonicalize(
            {"period": 3, "threshold": 6.0}
        ),
    )
    plan = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=context,
    )
    assert len(workspace.result_store) == 3
    state_key = next(
        key
        for key, result in workspace.result_store.results().items()
        if result.computation_identity.component_id == ComponentId("volatility.state")
    )
    state_result = workspace.result_store.results()[state_key]
    state_values = state_result.outputs[OutputId("state")].values
    distance_values = state_result.outputs[OutputId("distance_to_threshold")].values
    assert np.isnan(state_values[0])
    assert np.isnan(state_values[1])
    assert state_values[2] == 1.0
    assert distance_values[2] == pytest.approx((10.0 + 7.0 + 6.0) / 3.0 - 6.0)
