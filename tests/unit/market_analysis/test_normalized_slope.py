"""Tests for the causal Trend Normalized Slope component (IDEA-029)."""

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
from trading_framework.market_analysis.components.trend import NormalizedSlopeComponent
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


def _population_stdev(values: list[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _bars(closes: list[float]) -> list[MarketBar]:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, close in enumerate(closes):
        stamp = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close))),
                low=Price(Decimal(str(close))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
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


def _run(closes: list[float], *, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(closes))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = NormalizedSlopeComponent().parameter_schema.canonicalize(
        {"slope_period": 2, "volatility_period": 2, "baseline_period": 3}
    )
    request = ComponentRequest(
        component_id=ComponentId("trend.normalized_slope"),
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
        if result.computation_identity.component_id.value == "trend.normalized_slope":
            return result
    raise AssertionError("trend.normalized_slope not computed")


def test_normalized_slope_component_declares_shape() -> None:
    component = NormalizedSlopeComponent()
    assert component.component_id.value == "trend.normalized_slope"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_normalized_slope_matches_hand_computed_formula() -> None:
    closes = [100.0, 102.0, 105.0, 103.0, 108.0]
    result = _run(closes, source_id="normalized-slope-hand-computed")
    value = result.outputs[OutputId("value")].values

    # slope_period=2 collapses OLS slope to a plain first difference:
    # slope[3] = close[3] - close[2] = 103 - 105 = -2.
    expected_slope = closes[3] - closes[2]

    # volatility_period=2: rolling population stdev of log returns over the
    # window ending at index 3, i.e. returns at index 2 and 3.
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    expected_volatility = _population_stdev([returns[1], returns[2]])

    expected_value = expected_slope / expected_volatility
    assert value[3] == pytest.approx(expected_value)


def test_normalized_slope_is_zero_when_volatility_is_flat() -> None:
    closes = [100.0] * 5
    result = _run(closes, source_id="normalized-slope-flat")
    value = result.outputs[OutputId("value")].values
    assert value[3] == pytest.approx(0.0)


def test_normalized_slope_respects_warmup() -> None:
    closes = [100.0, 102.0, 105.0, 103.0, 108.0, 107.0]
    result = _run(closes, source_id="normalized-slope-warmup")
    value = result.outputs[OutputId("value")].values
    # baseline_period=3 dominates slope_period-1=1.
    assert result.warmup.warmup_bars == 3
    for index in range(3):
        assert np.isnan(value[index])
    for index in range(3, len(value)):
        assert not np.isnan(value[index])
