"""Tests for causal Session Range kernel and component."""

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
from trading_framework.market_analysis.adapters.numpy.session_range import session_range
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.components.structure import (
    NumpySessionRangeImplementation,
    SessionRangeComponent,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import ComponentValidationError
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_session_range_component
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def test_session_range_kernel_running_values_and_confirmed_end() -> None:
    open_ = np.array([9.0, 10.0, 11.0, 8.0], dtype=np.float64)
    high = np.array([9.5, 12.0, 13.0, 8.5], dtype=np.float64)
    low = np.array([8.5, 9.5, 10.0, 7.5], dtype=np.float64)
    close = np.array([9.2, 11.0, 12.5, 8.0], dtype=np.float64)
    is_rth = np.array([False, True, True, False])
    days = np.array([1, 1, 1, 1], dtype=np.int32)

    arrays = session_range(open_, high, low, close, is_rth=is_rth, trading_day_ordinal=days)

    assert np.isnan(arrays.session_high[0])
    assert arrays.session_open[1] == 10.0
    assert arrays.session_high[1] == 12.0
    assert arrays.session_low[1] == 9.5
    assert arrays.session_close[1] == 11.0
    assert arrays.session_range[1] == 2.5
    assert arrays.session_completed[1] == 0.0

    assert arrays.session_open[2] == 10.0
    assert arrays.session_high[2] == 13.0
    assert arrays.session_low[2] == 9.5
    assert arrays.session_close[2] == 12.5
    assert arrays.session_range[2] == 3.5
    assert arrays.session_completed[2] == 1.0

    assert np.isnan(arrays.session_high[3])
    assert np.isnan(arrays.session_completed[3])


def test_session_range_kernel_in_progress_session_is_not_completed() -> None:
    open_ = np.array([10.0, 11.0], dtype=np.float64)
    high = np.array([12.0, 13.0], dtype=np.float64)
    low = np.array([9.0, 10.0], dtype=np.float64)
    close = np.array([11.0, 12.0], dtype=np.float64)
    is_rth = np.array([True, True])
    days = np.array([1, 1], dtype=np.int32)

    arrays = session_range(open_, high, low, close, is_rth=is_rth, trading_day_ordinal=days)

    assert arrays.session_completed[0] == 0.0
    assert arrays.session_completed[1] == 0.0
    assert arrays.session_high[1] == 13.0


def test_session_range_kernel_new_trading_day_starts_new_group() -> None:
    open_ = np.array([10.0, 20.0], dtype=np.float64)
    high = np.array([11.0, 21.0], dtype=np.float64)
    low = np.array([9.0, 19.0], dtype=np.float64)
    close = np.array([10.5, 20.5], dtype=np.float64)
    is_rth = np.array([True, True])
    days = np.array([1, 2], dtype=np.int32)

    arrays = session_range(open_, high, low, close, is_rth=is_rth, trading_day_ordinal=days)

    assert arrays.session_completed[0] == 1.0
    assert arrays.session_open[1] == 20.0
    assert arrays.session_high[1] == 21.0
    assert arrays.session_completed[1] == 0.0


def _rth_bars() -> list[MarketBar]:
    # Monday 2024-06-03: 13:29 UTC is 09:29 EDT (outside); 13:30 is RTH start.
    stamps = [
        datetime(2024, 6, 3, 13, 29, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 31, tzinfo=UTC),
        datetime(2024, 6, 3, 20, 0, tzinfo=UTC),
    ]
    ohlc = [
        (100.0, 101.0, 99.0, 100.5),
        (110.0, 120.0, 109.0, 115.0),
        (115.0, 125.0, 114.0, 122.0),
        (90.0, 91.0, 89.0, 90.5),
    ]
    bars: list[MarketBar] = []
    for observed, (open_, high, low, close) in zip(stamps, ohlc, strict=True):
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=observed,
                available_at=observed.replace(minute=observed.minute + 1)
                if observed.minute < 59
                else observed.replace(hour=observed.hour + 1, minute=0),
            )
        )
    return bars


def _context() -> AnalysisContext:
    start = datetime(2024, 6, 3, 13, 29, tzinfo=UTC)
    end = datetime(2024, 6, 3, 20, 1, tzinfo=UTC)
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="session-range",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def test_session_range_component_requires_session_metadata() -> None:
    view = AnalysisDataView.from_bars(_rth_bars())
    workspace = AnalysisWorkspace(view)
    implementation = NumpySessionRangeImplementation()
    with pytest.raises(ComponentValidationError, match="session metadata is required"):
        implementation.compute(
            _context(),
            workspace.view_for(()),
            SessionRangeComponent().parameter_schema.canonicalize({}),
        )


def test_session_range_component_uses_injected_resolver() -> None:
    bars = _rth_bars()
    view = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_session_range_component(registry)
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("structure.session_range"),
        parameters=SessionRangeComponent().parameter_schema.canonicalize({}),
    )
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=_context().dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=_context().requested_range,
        ),
        (PlanningRequest.from_component_request(request),),
    )
    executed = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(),
        session_metadata=metadata,
        session_resolver=resolver,
    )
    result = next(iter(executed.result_store.results().values()))
    high = result.outputs[OutputId("session_high")].values
    completed = result.outputs[OutputId("session_completed")].values
    assert np.isnan(high[0])
    assert high[1] == 120.0
    assert high[2] == 125.0
    assert completed[1] == 0.0
    assert completed[2] == 1.0
    assert np.isnan(high[3])
