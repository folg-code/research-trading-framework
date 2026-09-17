"""Tests for the causal Volume Cumulative Trend component (formerly "Price Volume Trend")."""

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
from trading_framework.market_analysis.components.volume import CumulativeTrendComponent
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


def _bars(closes: list[float], volumes: list[int]) -> list[MarketBar]:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, (close, volume) in enumerate(zip(closes, volumes, strict=True)):
        stamp = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close + 1))),
                low=Price(Decimal(str(close - 1))),
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


def _run(closes: list[float], volumes: list[int], *, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(closes, volumes))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = CumulativeTrendComponent().parameter_schema.canonicalize({})
    request = ComponentRequest(
        component_id=ComponentId("volume.cumulative_trend"),
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
        if result.computation_identity.component_id.value == "volume.cumulative_trend":
            return result
    raise AssertionError("volume.cumulative_trend not computed")


def test_cumulative_trend_component_declares_shape() -> None:
    component = CumulativeTrendComponent()
    assert component.component_id.value == "volume.cumulative_trend"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_cumulative_trend_matches_hand_computed_formula() -> None:
    closes = [100.0, 102.0, 101.0, 105.0]
    volumes = [1000, 2000, 1500, 3000]
    result = _run(closes, volumes, source_id="cumulative-trend-hand-computed")
    value = result.outputs[OutputId("value")].values

    assert value[0] == pytest.approx(0.0)
    assert value[1] == pytest.approx(40.0)  # 2000 * (102-100)/100
    assert value[2] == pytest.approx(40.0 + 1500.0 * (101.0 - 102.0) / 102.0)
    assert value[3] == pytest.approx(value[2] + 3000.0 * (105.0 - 101.0) / 101.0)


def test_cumulative_trend_has_no_warmup() -> None:
    closes = [100.0, 101.0, 102.0]
    volumes = [1000, 1000, 1000]
    result = _run(closes, volumes, source_id="cumulative-trend-no-warmup")
    assert result.warmup.warmup_bars == 0
