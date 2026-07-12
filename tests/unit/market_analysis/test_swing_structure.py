"""Tests for Swing Structure component and kernel."""

from datetime import UTC, datetime, timedelta
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
from trading_framework.market_analysis.adapters.numpy.swing import detect_swing_structure
from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.availability import AvailabilityPolicy
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_swing_structure_component
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe


def _bar(
    observed_at: datetime,
    *,
    high: float,
    low: float,
    close: float | None = None,
) -> MarketBar:
    close_price = close if close is not None else (high + low) / 2.0
    return MarketBar(
        open=Price(Decimal(str(close_price))),
        high=Price(Decimal(str(high))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(close_price))),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at.replace(minute=observed_at.minute + 1)
        if observed_at.minute < 59
        else observed_at.replace(hour=observed_at.hour + 1, minute=0),
    )


def _bars_from_high_low(highs: list[float], lows: list[float]) -> list[MarketBar]:
    base = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for index, (high, low) in enumerate(zip(highs, lows, strict=True)):
        bars.append(
            _bar(
                base + timedelta(minutes=index),
                high=high,
                low=low,
            )
        )
    return bars


def _context(bar_count: int) -> AnalysisContext:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    end = start + timedelta(minutes=bar_count - 1)
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def _planning_context(bar_count: int) -> PlanningContext:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    end = start + timedelta(minutes=bar_count - 1)
    return PlanningContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
    )


def test_swing_structure_component_contract() -> None:
    component = SwingStructureComponent()
    parameters = component.parameter_schema.canonicalize({"pivot_range": 2})
    assert component.kind is ComponentKind.STRUCTURE
    assert component.causality is Causality.DELAYED
    assert {dep.field for dep in component.data_dependencies(parameters)} == {"high", "low"}
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert "swing_high_event" in output_ids
    assert "latest_higher_high_level" in output_ids
    assert "hh" not in output_ids


def test_swing_high_emitted_on_available_index_not_observed_index() -> None:
    highs = np.array([10.0, 20.0, 15.0, 25.0, 20.0, 15.0], dtype=np.float64)
    lows = np.array([9.0, 19.0, 14.0, 24.0, 19.0, 14.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    assert result.swing_high_event[3] == pytest.approx(0.0)
    assert result.swing_high_event[5] == pytest.approx(1.0)
    assert result.swing_high_price[5] == pytest.approx(25.0)
    assert result.swing_high_observed_index[5] == pytest.approx(3.0)
    assert np.isnan(result.swing_high_price[3])


def test_higher_high_and_lower_high_classification_events() -> None:
    highs = np.array([1.0, 5.0, 3.0, 8.0, 4.0, 3.0, 2.0], dtype=np.float64)
    lows = np.zeros(7, dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=1)
    assert result.higher_high_event[4] == pytest.approx(1.0)
    assert result.latest_higher_high_level[4] == pytest.approx(8.0)
    assert result.lower_high_event[5] == pytest.approx(1.0)
    assert result.latest_lower_high_level[5] == pytest.approx(4.0)


def test_equal_swing_high_updates_latest_but_not_classification() -> None:
    highs = np.array([10.0, 20.0, 15.0, 25.0, 20.0, 25.0, 18.0, 16.0], dtype=np.float64)
    lows = np.array([9.0, 19.0, 14.0, 24.0, 19.0, 24.0, 17.0, 15.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    assert result.swing_high_event[7] == pytest.approx(1.0)
    assert result.latest_swing_high_level[7] == pytest.approx(25.0)
    assert result.higher_high_event[7] == pytest.approx(0.0)
    assert result.lower_high_event[7] == pytest.approx(0.0)


def test_simultaneous_swing_high_and_low_events_emit_both() -> None:
    highs = np.array([10.0, 12.0, 11.0, 13.0], dtype=np.float64)
    lows = np.array([9.0, 8.0, 11.0, 8.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=1)
    detection_index = 2
    assert result.swing_high_event[detection_index] == pytest.approx(1.0)
    assert result.swing_low_event[detection_index] == pytest.approx(1.0)


def test_latest_swing_levels_forward_fill_after_confirmation() -> None:
    highs = np.array([10.0, 20.0, 15.0, 25.0, 20.0, 15.0], dtype=np.float64)
    lows = np.array([9.0, 19.0, 14.0, 24.0, 19.0, 14.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    assert result.latest_swing_high_level[5] == pytest.approx(25.0)
    assert np.isnan(result.latest_swing_high_level[4])


def test_executor_runs_swing_structure_with_delayed_availability() -> None:
    highs = [10.0, 20.0, 15.0, 25.0, 20.0, 15.0]
    lows = [9.0, 19.0, 14.0, 24.0, 19.0, 14.0]
    bars = _bars_from_high_low(highs, lows)
    registry = ComponentRegistry()
    register_swing_structure_component(registry)
    view = AnalysisDataView.from_bars(bars)
    parameters = SwingStructureComponent().parameter_schema.canonicalize({"pivot_range": 2})
    request = ComponentRequest(component_id=ComponentId("structure.swing"), parameters=parameters)
    plan = DependencyPlanner(registry).build_plan(
        _planning_context(len(bars)),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(len(bars)),
    )
    result = next(iter(workspace.result_store.results().values()))
    assert result.availability.policy is AvailabilityPolicy.DELAYED_BARS
    assert result.availability.delay_bars == 2
    swing_high = result.outputs[OutputId("swing_high_event")]
    assert swing_high.available_at is not None
    assert swing_high.values[5] == pytest.approx(1.0)


def test_swing_high_with_pivot_range_15_confirms_on_available_index() -> None:
    bar_count = 35
    highs = np.full(bar_count, 50.0, dtype=np.float64)
    highs[15] = 100.0
    lows = highs - 1.0
    result = detect_swing_structure(highs, lows, pivot_range=15)
    detection_index = 30
    observed_index = 15
    assert result.swing_high_event[detection_index] == pytest.approx(1.0)
    assert result.swing_high_price[detection_index] == pytest.approx(100.0)
    assert result.swing_high_observed_index[detection_index] == pytest.approx(float(observed_index))
    assert result.swing_high_event[observed_index] == pytest.approx(0.0)
    assert np.isnan(result.swing_high_price[observed_index])


def test_executor_runs_swing_structure_with_pivot_range_15() -> None:
    bar_count = 35
    highs = [50.0] * bar_count
    highs[15] = 100.0
    lows = [value - 1.0 for value in highs]
    bars = _bars_from_high_low(highs, lows)
    registry = ComponentRegistry()
    register_swing_structure_component(registry)
    view = AnalysisDataView.from_bars(bars)
    parameters = SwingStructureComponent().parameter_schema.canonicalize({"pivot_range": 15})
    request = ComponentRequest(component_id=ComponentId("structure.swing"), parameters=parameters)
    plan = DependencyPlanner(registry).build_plan(
        _planning_context(len(bars)),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(len(bars)),
    )
    result = next(iter(workspace.result_store.results().values()))
    assert result.availability.delay_bars == 15
    assert result.warmup.warmup_bars == 15
    swing_high = result.outputs[OutputId("swing_high_event")]
    assert swing_high.values[30] == pytest.approx(1.0)


def test_swing_low_emitted_on_available_index_not_observed_index() -> None:
    highs = np.array([10.0, 12.0, 11.0, 13.0, 12.0, 11.0], dtype=np.float64)
    lows = np.array([9.0, 8.0, 11.0, 7.0, 10.0, 9.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    assert result.swing_low_event[3] == pytest.approx(0.0)
    assert result.swing_low_event[5] == pytest.approx(1.0)
    assert result.swing_low_price[5] == pytest.approx(7.0)
    assert result.swing_low_observed_index[5] == pytest.approx(3.0)
    assert np.isnan(result.swing_low_price[3])


def test_higher_low_and_lower_low_classification_events() -> None:
    highs = np.ones(9, dtype=np.float64) * 20.0
    lows = np.array([10.0, 8.0, 5.0, 7.0, 9.0, 6.0, 4.0, 3.0, 5.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=1)
    assert result.higher_low_event[4] == pytest.approx(1.0)
    assert result.latest_higher_low_level[4] == pytest.approx(7.0)
    assert result.lower_low_event[8] == pytest.approx(1.0)
    assert result.latest_lower_low_level[8] == pytest.approx(3.0)


def test_first_swing_high_emits_event_without_classification() -> None:
    highs = np.array([10.0, 20.0, 15.0, 25.0, 20.0, 15.0], dtype=np.float64)
    lows = np.array([9.0, 19.0, 14.0, 24.0, 19.0, 14.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    first_detection = 5
    assert result.swing_high_event[first_detection] == pytest.approx(1.0)
    assert result.higher_high_event[first_detection] == pytest.approx(0.0)
    assert result.lower_high_event[first_detection] == pytest.approx(0.0)
    assert np.isnan(result.latest_higher_high_level[first_detection])


def test_nan_input_rejected_by_kernel() -> None:
    highs = np.array([10.0, np.nan, 15.0], dtype=np.float64)
    lows = np.array([9.0, 14.0, 14.0], dtype=np.float64)
    with pytest.raises(ValueError, match="NaN"):
        detect_swing_structure(highs, lows, pivot_range=1)


def test_observed_index_never_receives_event_values() -> None:
    highs = np.array([10.0, 20.0, 15.0, 25.0, 20.0, 15.0], dtype=np.float64)
    lows = np.array([9.0, 19.0, 14.0, 24.0, 19.0, 14.0], dtype=np.float64)
    result = detect_swing_structure(highs, lows, pivot_range=2)
    observed_index = 3
    assert result.swing_high_event[observed_index] == pytest.approx(0.0)
    assert np.isnan(result.swing_high_price[observed_index])
    assert np.isnan(result.latest_swing_high_level[observed_index])
