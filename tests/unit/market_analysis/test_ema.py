"""Tests for the EMA trend feature component."""

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
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.kernels import ema
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_ema_component
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe


def _bars() -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    closes = [102.0, 107.0, 105.0, 101.0, 102.0]
    bars: list[MarketBar] = []
    for index, close in enumerate(closes):
        observed = base.replace(hour=index)
        available = observed.replace(hour=index, minute=1)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close + 1))),
                low=Price(Decimal(str(close - 1))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=observed,
                available_at=available,
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


def test_ema_kernel_seeds_with_sma() -> None:
    close = np.array([102.0, 107.0, 105.0, 101.0, 102.0], dtype=np.float64)
    values = ema(close, 3)
    assert np.isnan(values[0])
    assert np.isnan(values[1])
    assert values[2] == pytest.approx(np.mean(close[:3]))


def test_ema_component_depends_on_close_prices() -> None:
    component = EmaComponent()
    parameters = component.parameter_schema.canonicalize({"period": 20})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()


def test_executor_runs_ema_component() -> None:
    registry = ComponentRegistry()
    register_ema_component(registry)
    view = AnalysisDataView.from_bars(_bars())
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("trend.ema"),
        parameters=EmaComponent().parameter_schema.canonicalize({"period": 3}),
    )
    plan = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(),
    )
    assert len(workspace.result_store) == 1
    ema_result = next(iter(workspace.result_store.results().values()))
    ema_values = ema_result.outputs[OutputId("value")].values
    close = np.array([102.0, 107.0, 105.0, 101.0, 102.0], dtype=np.float64)
    expected = ema(close, 3)
    assert ema_values[2] == pytest.approx(expected[2])
    assert ema_values[4] == pytest.approx(expected[4])
