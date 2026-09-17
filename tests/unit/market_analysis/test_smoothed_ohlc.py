"""Tests for the causal Candle Smoothed OHLC component."""

from datetime import UTC, datetime
from decimal import Decimal

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
from trading_framework.market_analysis.components.candle import SmoothedOhlcComponent
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
    rows: list[tuple[datetime, float, float, float, float]], *, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = SmoothedOhlcComponent().parameter_schema.canonicalize({})
    request = ComponentRequest(
        component_id=ComponentId("candle.smoothed_ohlc"),
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
        if result.computation_identity.component_id.value == "candle.smoothed_ohlc":
            return result
    raise AssertionError("candle.smoothed_ohlc not computed")


def test_smoothed_ohlc_component_declares_shape() -> None:
    component = SmoothedOhlcComponent()
    assert component.component_id.value == "candle.smoothed_ohlc"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"open", "high", "low", "close"}


def test_smoothed_ohlc_matches_hand_computed_formula() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 105.0, 98.0, 102.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 103.0, 108.0, 101.0, 106.0),
        (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 105.0, 107.0, 100.0, 101.0),
    ]
    result = _run(rows, source_id="smoothed-ohlc-hand-computed")
    smoothed_open = result.outputs[OutputId("open")].values
    smoothed_high = result.outputs[OutputId("high")].values
    smoothed_low = result.outputs[OutputId("low")].values
    smoothed_close = result.outputs[OutputId("close")].values

    assert smoothed_close[0] == pytest.approx(101.25)
    assert smoothed_open[0] == pytest.approx(101.0)
    assert smoothed_high[0] == pytest.approx(105.0)
    assert smoothed_low[0] == pytest.approx(98.0)

    assert smoothed_close[1] == pytest.approx(104.5)
    assert smoothed_open[1] == pytest.approx(101.125)
    assert smoothed_high[1] == pytest.approx(108.0)
    assert smoothed_low[1] == pytest.approx(101.0)

    assert smoothed_close[2] == pytest.approx(103.25)
    assert smoothed_open[2] == pytest.approx(102.8125)
    assert smoothed_high[2] == pytest.approx(107.0)
    assert smoothed_low[2] == pytest.approx(100.0)


def test_smoothed_ohlc_has_no_warmup() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 105.0, 98.0, 102.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 103.0, 108.0, 101.0, 106.0),
    ]
    result = _run(rows, source_id="smoothed-ohlc-no-warmup")
    assert result.warmup.warmup_bars == 0
    for output_id in ("open", "high", "low", "close"):
        values = result.outputs[OutputId(output_id)].values
        assert all(value == value for value in values)  # no NaN anywhere
