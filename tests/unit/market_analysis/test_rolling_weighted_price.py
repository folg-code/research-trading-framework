"""Tests for the causal Volume Rolling Weighted Price component."""

import math
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
from trading_framework.market_analysis.components.volume import RollingWeightedPriceComponent
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


def _bars(rows: list[tuple[float, float, float, int]]) -> list[MarketBar]:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, (high, low, close, volume) in enumerate(rows):
        stamp = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(volume),
                observed_at=stamp,
                available_at=stamp.replace(minute=stamp.minute + 1)
                if stamp.minute < 59
                else stamp.replace(hour=stamp.hour + 1, minute=0),
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
    rows: list[tuple[float, float, float, int]], *, period: int, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = RollingWeightedPriceComponent().parameter_schema.canonicalize(
        {"period": period, "band_multiplier": 2.0}
    )
    request = ComponentRequest(
        component_id=ComponentId("volume.rolling_weighted_price"),
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
        if result.computation_identity.component_id.value == "volume.rolling_weighted_price":
            return result
    raise AssertionError("volume.rolling_weighted_price not computed")


def test_rolling_weighted_price_component_declares_shape() -> None:
    component = RollingWeightedPriceComponent()
    assert component.component_id.value == "volume.rolling_weighted_price"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value", "deviation", "upper_band", "lower_band"}


def test_rolling_weighted_price_matches_hand_computed_formula() -> None:
    # typical_price = (high + low + close) / 3: bar0 -> 100.0, bar1 -> 104.0,
    # bar2 -> 102.0.
    rows = [
        (101.0, 99.0, 100.0, 1000),
        (105.0, 103.0, 104.0, 3000),
        (103.0, 101.0, 102.0, 2000),
    ]
    result = _run(rows, period=2, source_id="rwp-hand-computed")
    value = result.outputs[OutputId("value")].values
    deviation = result.outputs[OutputId("deviation")].values
    upper_band = result.outputs[OutputId("upper_band")].values
    lower_band = result.outputs[OutputId("lower_band")].values

    assert np.isnan(value[0])

    # index 1: window = bars 0,1. vwap = (100*1000 + 104*3000) / 4000 = 103.0.
    assert value[1] == pytest.approx(103.0)
    expected_deviation_1 = math.sqrt((1000.0 * 9.0 + 3000.0 * 1.0) / 4000.0)
    assert deviation[1] == pytest.approx(expected_deviation_1)
    assert upper_band[1] == pytest.approx(103.0 + 2.0 * expected_deviation_1)
    assert lower_band[1] == pytest.approx(103.0 - 2.0 * expected_deviation_1)

    # index 2: window = bars 1,2. vwap = (104*3000 + 102*2000) / 5000 = 103.2.
    assert value[2] == pytest.approx(103.2)
    expected_deviation_2 = math.sqrt((3000.0 * 0.64 + 2000.0 * 1.44) / 5000.0)
    assert deviation[2] == pytest.approx(expected_deviation_2)


def test_rolling_weighted_price_respects_warmup() -> None:
    period = 3
    rows = [(101.0, 99.0, 100.0, 1000) for _ in range(5)]
    result = _run(rows, period=period, source_id="rwp-warmup")
    value = result.outputs[OutputId("value")].values
    assert result.warmup.warmup_bars == period - 1
    for index in range(period - 1):
        assert np.isnan(value[index])
    for index in range(period - 1, len(value)):
        assert not np.isnan(value[index])


def test_rolling_weighted_price_is_nan_for_a_zero_volume_window() -> None:
    period = 2
    rows = [
        (101.0, 99.0, 100.0, 0),
        (105.0, 103.0, 104.0, 0),
    ]
    result = _run(rows, period=period, source_id="rwp-zero-volume")
    value = result.outputs[OutputId("value")].values
    deviation = result.outputs[OutputId("deviation")].values
    assert np.isnan(value[period - 1])
    assert np.isnan(deviation[period - 1])
