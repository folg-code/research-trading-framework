"""Tests for the ATR-normalized causal Opening Gap component."""

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
from trading_framework.market_analysis.components.structure import OpeningGapComponent
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


def _run(bars: list[MarketBar], *, period: int, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = OpeningGapComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("structure.opening_gap"),
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
        if result.computation_identity.component_id.value == "structure.opening_gap":
            return result
    raise AssertionError("structure.opening_gap not computed")


def test_opening_gap_component_declares_shape() -> None:
    component = OpeningGapComponent()
    assert component.component_id.value == "structure.opening_gap"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"gap_atr"}


def test_opening_gap_computes_atr_normalized_value() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.5),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 105.0, 106.0, 104.0, 105.5),
        (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 103.0, 107.0, 102.0, 104.0),
    ]
    result = _run(_bars(rows), period=1, source_id="opening-gap-values")

    gap_atr = result.outputs[OutputId("gap_atr")].values

    # Bar 1: gap = open(105) - prev_close(100.5) = 4.5.
    # TR(period=1) at bar 1: high=106, low=104, prev_close=100.5
    # -> TR = max(2, |106-100.5|=5.5, |104-100.5|=3.5) = 5.5
    assert gap_atr[1] == pytest.approx(4.5 / 5.5)

    # Bar 2: gap = open(103) - prev_close(105.5) = -2.5.
    # TR(period=1) at bar 2: high=107, low=102, prev_close=105.5
    # -> TR = max(5, |107-105.5|=1.5, |102-105.5|=3.5) = 5
    assert gap_atr[2] == pytest.approx(-2.5 / 5.0)


def test_opening_gap_respects_atr_warmup() -> None:
    period = 14
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(20):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(_bars(rows), period=period, source_id="opening-gap-warmup")

    gap_atr = result.outputs[OutputId("gap_atr")].values

    warmup_bars = period - 1
    assert result.warmup.warmup_bars == warmup_bars
    assert result.validity.valid_from_index == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(gap_atr[index])
    for index in range(warmup_bars, len(gap_atr)):
        assert not np.isnan(gap_atr[index])
