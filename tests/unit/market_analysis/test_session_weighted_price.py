"""Tests for the causal Volume Session Weighted Price component (IDEA-031)."""

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
from trading_framework.market_analysis.adapters.numpy.session_weighted_price import (
    session_weighted_price,
)
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.components.volume import SessionWeightedPriceComponent
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


def _weighted_value_and_deviation(prices: list[float], volumes: list[float]) -> tuple[float, float]:
    total_volume = sum(volumes)
    value = sum(p * v for p, v in zip(prices, volumes, strict=True)) / total_volume
    mean_of_squares = sum(p * p * v for p, v in zip(prices, volumes, strict=True)) / total_volume
    deviation = math.sqrt(max(mean_of_squares - value * value, 0.0))
    return value, deviation


def test_session_weighted_price_component_declares_shape() -> None:
    component = SessionWeightedPriceComponent()
    assert component.component_id == ComponentId("volume.session_weighted_price")
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value", "deviation", "upper_band", "lower_band"}


def test_session_weighted_price_is_nan_outside_rth() -> None:
    typical_price = np.array([100.0, 100.0, 104.0, 100.0], dtype=np.float64)
    volume = np.array([1000.0, 10.0, 20.0, 1000.0], dtype=np.float64)
    is_rth = np.array([False, True, True, False])
    trading_day_ordinal = np.array([1, 1, 1, 1], dtype=np.int32)

    arrays = session_weighted_price(
        typical_price,
        volume,
        is_rth=is_rth,
        trading_day_ordinal=trading_day_ordinal,
        band_multiplier=2.0,
    )
    assert np.isnan(arrays.value[0])
    assert np.isnan(arrays.value[3])
    assert not np.isnan(arrays.value[1])
    assert not np.isnan(arrays.value[2])


def test_session_weighted_price_matches_hand_computed_and_accumulates() -> None:
    typical_price = np.array([100.0, 104.0], dtype=np.float64)
    volume = np.array([10.0, 20.0], dtype=np.float64)
    is_rth = np.array([True, True])
    trading_day_ordinal = np.array([1, 1], dtype=np.int32)

    arrays = session_weighted_price(
        typical_price,
        volume,
        is_rth=is_rth,
        trading_day_ordinal=trading_day_ordinal,
        band_multiplier=2.0,
    )

    expected_value_1, expected_deviation_1 = _weighted_value_and_deviation([100.0], [10.0])
    assert arrays.value[0] == pytest.approx(expected_value_1)
    assert arrays.deviation[0] == pytest.approx(expected_deviation_1)
    assert arrays.upper_band[0] == pytest.approx(expected_value_1 + 2.0 * expected_deviation_1)
    assert arrays.lower_band[0] == pytest.approx(expected_value_1 - 2.0 * expected_deviation_1)

    # bar 1 accumulates BOTH bars of the session, not a rolling window.
    expected_value_2, expected_deviation_2 = _weighted_value_and_deviation(
        [100.0, 104.0], [10.0, 20.0]
    )
    assert arrays.value[1] == pytest.approx(expected_value_2)
    assert arrays.deviation[1] == pytest.approx(expected_deviation_2)


def test_session_weighted_price_resets_at_a_new_session_boundary() -> None:
    # A big first session, then a new trading day: the new session's VWAP
    # must not carry over any of the prior session's accumulated sums.
    typical_price = np.array([100.0, 104.0, 200.0], dtype=np.float64)
    volume = np.array([10.0, 20.0, 5.0], dtype=np.float64)
    is_rth = np.array([True, True, True])
    trading_day_ordinal = np.array([1, 1, 2], dtype=np.int32)

    arrays = session_weighted_price(
        typical_price,
        volume,
        is_rth=is_rth,
        trading_day_ordinal=trading_day_ordinal,
        band_multiplier=2.0,
    )
    assert arrays.value[2] == pytest.approx(200.0)
    assert arrays.deviation[2] == pytest.approx(0.0)


def test_session_weighted_price_resets_after_a_non_rth_gap_on_the_same_day() -> None:
    typical_price = np.array([100.0, 104.0, 999.0, 200.0], dtype=np.float64)
    volume = np.array([10.0, 20.0, 1000.0, 5.0], dtype=np.float64)
    is_rth = np.array([True, True, False, True])
    trading_day_ordinal = np.array([1, 1, 1, 1], dtype=np.int32)

    arrays = session_weighted_price(
        typical_price,
        volume,
        is_rth=is_rth,
        trading_day_ordinal=trading_day_ordinal,
        band_multiplier=2.0,
    )
    # bar 3 starts a fresh session even though the trading day is unchanged.
    assert arrays.value[3] == pytest.approx(200.0)
    assert arrays.deviation[3] == pytest.approx(0.0)


def test_session_weighted_price_is_nan_for_a_zero_volume_session_so_far() -> None:
    typical_price = np.array([100.0], dtype=np.float64)
    volume = np.array([0.0], dtype=np.float64)
    is_rth = np.array([True])
    trading_day_ordinal = np.array([1], dtype=np.int32)

    arrays = session_weighted_price(
        typical_price,
        volume,
        is_rth=is_rth,
        trading_day_ordinal=trading_day_ordinal,
        band_multiplier=2.0,
    )
    assert np.isnan(arrays.value[0])
    assert np.isnan(arrays.deviation[0])


def _bars(rows: list[tuple[datetime, float, float]]) -> list[MarketBar]:
    bars: list[MarketBar] = []
    for observed, close, volume in rows:
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close))),
                low=Price(Decimal(str(close))),
                close=Price(Decimal(str(close))),
                volume=Volume(int(volume)),
                observed_at=observed,
                available_at=observed.replace(minute=observed.minute + 1)
                if observed.minute < 59
                else observed.replace(hour=observed.hour + 1, minute=0),
            )
        )
    return bars


def test_session_weighted_price_integrates_through_the_registry() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 10.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 104.0, 20.0),
    ]
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = SessionWeightedPriceComponent().parameter_schema.canonicalize({})
    request = ComponentRequest(
        component_id=ComponentId("volume.session_weighted_price"),
        parameters=parameters,
    )
    context = AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="session-weighted-price-integration",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=view.timestamps[0], end=view.timestamps[-1]),
        computation_range=TimeRange(start=view.timestamps[0], end=view.timestamps[-1]),
        engine_version="0.1.0",
    )
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
    result: AnalysisResult | None = None
    for candidate in executed.result_store.results().values():
        if candidate.computation_identity.component_id.value == "volume.session_weighted_price":
            result = candidate
    assert result is not None
    value = result.outputs[OutputId("value")].values
    expected_value, _ = _weighted_value_and_deviation([100.0, 104.0], [10.0, 20.0])
    assert value[1] == pytest.approx(expected_value)
