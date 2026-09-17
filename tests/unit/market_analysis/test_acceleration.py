"""Tests for the causal Volatility Acceleration component."""

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
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.components.volatility import AccelerationComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_mvp_components
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _bars(rows: list[tuple[datetime, float, float, float, float]]) -> list[MarketBar]:
    bars: list[MarketBar] = []
    for observed, open_, high, low, close in rows:
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


def _context(*, start: datetime, end: datetime, source_id: str) -> AnalysisContext:
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id=source_id,
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def _run(
    rows: list[tuple[datetime, float, float, float, float]], *, period: int, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = AccelerationComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("volatility.acceleration"),
        parameters=parameters,
    )
    context = _context(start=view.timestamps[0], end=view.timestamps[-1], source_id=source_id)
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=context.dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=context.requested_range,
        ),
        (PlanningRequest.from_component_request(request),),
    )
    executed = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=context,
        session_metadata=metadata,
        session_resolver=resolver,
    )
    for result in executed.result_store.results().values():
        if result.computation_identity.component_id.value == "volatility.acceleration":
            return result
    raise AssertionError("volatility.acceleration not computed")


def test_acceleration_component_declares_shape() -> None:
    component = AccelerationComponent()
    assert component.component_id.value == "volatility.acceleration"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_acceleration_is_the_first_difference_of_atr() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 105.0, 100.0, 103.0),
        (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 103.0, 104.0, 101.0, 102.0),
    ]
    result = _run(rows, period=1, source_id="acceleration-first-diff")
    value = result.outputs[OutputId("value")].values

    # ATR(period=1) = true range: [2, 5, 3] (bar 0 uses its own close as
    # prior close, per true_range's convention).
    assert np.isnan(value[0])
    assert value[1] == pytest.approx(5.0 - 2.0)
    assert value[2] == pytest.approx(3.0 - 5.0)


def test_acceleration_respects_warmup() -> None:
    period = 5
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(8):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(rows, period=period, source_id="acceleration-warmup")
    value = result.outputs[OutputId("value")].values
    assert result.warmup.warmup_bars == period
    for index in range(period):
        assert np.isnan(value[index])
    for index in range(period, len(value)):
        assert not np.isnan(value[index])
