"""Tests for the OLS slope trend feature component."""

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
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
from trading_framework.market_analysis.adapters.numpy.kernels import ols_slope
from trading_framework.market_analysis.components.trend import SlopeComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_slope_component
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


def test_ols_slope_kernel_matches_polyfit_on_linear_close() -> None:
    close = np.array([10.0, 12.0, 14.0, 16.0, 18.0], dtype=np.float64)
    values = ols_slope(close, 3)
    assert np.isnan(values[0])
    assert np.isnan(values[1])
    expected = np.polyfit(np.arange(3), close[2:5], 1)[0]
    assert values[4] == pytest.approx(expected)
    assert values[4] == pytest.approx(2.0)


def test_ols_slope_kernel_rejects_short_windows() -> None:
    close = np.array([10.0, 11.0], dtype=np.float64)
    assert np.all(np.isnan(ols_slope(close, 3)))
    assert np.all(np.isnan(ols_slope(close, 1)))


def test_slope_component_depends_on_close_prices() -> None:
    component = SlopeComponent()
    parameters = component.parameter_schema.canonicalize({"period": 20})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()
    assert parameters.get("period") == 20


def test_slope_period_minimum_is_two() -> None:
    component = SlopeComponent()
    with pytest.raises(ValidationError, match="period"):
        component.parameter_schema.canonicalize({"period": 1})


def test_executor_runs_slope_component() -> None:
    registry = ComponentRegistry()
    register_slope_component(registry)
    view = AnalysisDataView.from_bars(_bars())
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("trend.slope"),
        parameters=SlopeComponent().parameter_schema.canonicalize({"period": 3}),
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
    slope_result = next(iter(workspace.result_store.results().values()))
    slope_values = slope_result.outputs[OutputId("value")].values
    close = np.array([102.0, 107.0, 105.0, 101.0, 102.0], dtype=np.float64)
    expected = ols_slope(close, 3)
    assert slope_values[2] == pytest.approx(expected[2])
    assert slope_values[4] == pytest.approx(expected[4])
