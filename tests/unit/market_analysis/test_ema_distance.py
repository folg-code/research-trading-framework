"""Tests for the ATR-normalized causal EMA Distance component."""

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
from trading_framework.market_analysis.components.trend import EmaDistanceComponent
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
    bars: list[MarketBar],
    *,
    period: int,
    atr_period: int,
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = EmaDistanceComponent().parameter_schema.canonicalize(
        {"period": period, "atr_period": atr_period}
    )
    request = ComponentRequest(
        component_id=ComponentId("trend.ema_distance"),
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
        if result.computation_identity.component_id.value == "trend.ema_distance":
            return result
    raise AssertionError("trend.ema_distance not computed")


def test_ema_distance_component_declares_shape() -> None:
    component = EmaDistanceComponent()
    assert component.component_id.value == "trend.ema_distance"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"distance_atr"}


def test_ema_distance_is_causal_and_signed() -> None:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(20):
        stamp = start.replace(minute=start.minute + minute)
        # A steady uptrend: close pulls away from a lagging EMA, so distance
        # should be positive and (loosely) increasing.
        base = 100.0 + minute * 2.0
        rows.append((stamp, base, base + 1.0, base - 1.0, base))

    result = _run(_bars(rows), period=5, atr_period=5, source_id="ema-distance-causal")
    distance = result.outputs[OutputId("distance_atr")].values

    warmup_bars = max(5 - 1, 5 - 1)
    for index in range(warmup_bars, len(distance)):
        assert not np.isnan(distance[index])
        # Close is above a lagging EMA in a steady uptrend: signed positive.
        assert distance[index] > 0.0


def test_ema_distance_respects_max_ema_atr_warmup() -> None:
    period = 20
    atr_period = 5
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(25):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(
        _bars(rows),
        period=period,
        atr_period=atr_period,
        source_id="ema-distance-warmup",
    )
    distance = result.outputs[OutputId("distance_atr")].values

    warmup_bars = max(period - 1, atr_period - 1)
    assert warmup_bars == period - 1  # EMA's longer warmup dominates here
    assert result.warmup.warmup_bars == warmup_bars
    assert result.validity.valid_from_index == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(distance[index])
    for index in range(warmup_bars, len(distance)):
        assert not np.isnan(distance[index])


def test_ema_distance_zero_atr_is_defined_not_nan() -> None:
    # A perfectly flat instrument: true range and therefore ATR is exactly
    # 0.0 once warmup completes. The convention is a defined 0.0, not an
    # incidental inf/NaN from dividing by zero.
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(10):
        stamp = start.replace(minute=start.minute + minute)
        rows.append((stamp, 100.0, 100.0, 100.0, 100.0))

    result = _run(_bars(rows), period=3, atr_period=3, source_id="ema-distance-zero-atr")
    distance = result.outputs[OutputId("distance_atr")].values

    warmup_bars = max(3 - 1, 3 - 1)
    for index in range(warmup_bars, len(distance)):
        assert distance[index] == pytest.approx(0.0)
