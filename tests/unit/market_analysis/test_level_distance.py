"""Tests for the ATR-normalized causal Level Distance component."""

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
from trading_framework.market_analysis.components.structure import LevelDistanceComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
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


def _run(bars: list[MarketBar], *, period: int, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = LevelDistanceComponent().parameter_schema.canonicalize({"period": period})
    from trading_framework.market_analysis.models.request import ComponentRequest

    request = ComponentRequest(
        component_id=ComponentId("structure.level_distance"),
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
        if result.computation_identity.component_id.value == "structure.level_distance":
            return result
    raise AssertionError("structure.level_distance not computed")


def test_level_distance_component_declares_shape() -> None:
    component = LevelDistanceComponent()
    assert component.component_id.value == "structure.level_distance"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"distance_to_session_high_atr", "distance_to_session_low_atr"}


def test_level_distance_is_causal_at_session_boundary() -> None:
    # Monday 2024-06-03: 13:29 UTC is 09:29 EDT (outside RTH); 13:30 is RTH start.
    rows = [
        (datetime(2024, 6, 3, 13, 29, tzinfo=UTC), 100.0, 101.0, 99.0, 100.5),
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 110.0, 120.0, 109.0, 115.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 115.0, 125.0, 114.0, 122.0),
        (datetime(2024, 6, 3, 20, 0, tzinfo=UTC), 90.0, 91.0, 89.0, 90.5),
    ]
    result = _run(_bars(rows), period=1, source_id="level-distance-causal")

    distance_high = result.outputs[OutputId("distance_to_session_high_atr")].values
    distance_low = result.outputs[OutputId("distance_to_session_low_atr")].values

    # Outside RTH: no running session extremes, so both outputs are NaN.
    assert np.isnan(distance_high[0])
    assert np.isnan(distance_low[0])
    assert np.isnan(distance_high[3])
    assert np.isnan(distance_low[3])

    # Bar 1 is the FIRST RTH bar: the running session high is bar 1's own high
    # (120), not bar 2's later, higher high (125) -- proving no look-ahead into
    # the eventual full-session extreme.
    # TR/ATR(period=1) at bar 1: high=120, low=109, prev_close=100.5 (bar 0's
    # close) -> TR = max(11, |120-100.5|, |109-100.5|) = 19.5
    assert distance_high[1] == pytest.approx((120.0 - 115.0) / 19.5)
    assert distance_low[1] == pytest.approx((115.0 - 109.0) / 19.5)

    # Bar 2: running session high/low now folds in bar 2 (125 / 109).
    # TR(period=1) at bar 2: high=125, low=114, prev_close=115 (bar 1's close)
    # -> TR = max(11, |125-115|, |114-115|) = 11
    assert distance_high[2] == pytest.approx((125.0 - 122.0) / 11.0)
    assert distance_low[2] == pytest.approx((122.0 - 109.0) / 11.0)


def test_level_distance_respects_atr_warmup() -> None:
    period = 14
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(20):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(_bars(rows), period=period, source_id="level-distance-warmup")

    distance_high = result.outputs[OutputId("distance_to_session_high_atr")].values
    distance_low = result.outputs[OutputId("distance_to_session_low_atr")].values

    warmup_bars = period - 1
    assert result.warmup.warmup_bars == warmup_bars
    assert result.validity.valid_from_index == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(distance_high[index])
        assert np.isnan(distance_low[index])
    for index in range(warmup_bars, len(distance_high)):
        assert not np.isnan(distance_high[index])
        assert not np.isnan(distance_low[index])
