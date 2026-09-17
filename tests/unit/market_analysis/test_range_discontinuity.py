"""Tests for the causal Structure Range Discontinuity ("fair value gap") component."""

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
from trading_framework.market_analysis.components.structure import RangeDiscontinuityComponent
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
    parameters = RangeDiscontinuityComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("structure.range_discontinuity"),
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
        if result.computation_identity.component_id.value == "structure.range_discontinuity":
            return result
    raise AssertionError("structure.range_discontinuity not computed")


def test_range_discontinuity_component_declares_shape() -> None:
    component = RangeDiscontinuityComponent()
    assert component.component_id.value == "structure.range_discontinuity"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"gap_up_event", "gap_down_event"}


def test_range_discontinuity_flags_up_and_down_gaps() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.5),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 105.0, 112.0, 104.0, 110.0),
        (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 111.0, 115.0, 110.0, 113.0),
        (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 95.0, 96.0, 90.0, 91.0),
    ]
    result = _run(_bars(rows), period=1, source_id="range-discontinuity-flags")

    gap_up = result.outputs[OutputId("gap_up_event")].values
    gap_down = result.outputs[OutputId("gap_down_event")].values

    # Bar 2: low(110) - high[bar0](101) = 9, well above 0.1 * TR(1)@bar2 = 0.5.
    assert list(gap_up) == [0.0, 0.0, 1.0, 0.0]
    # Bar 3: low[bar1](104) - high(96) = 8, well above 0.1 * TR(1)@bar3 = 2.3.
    assert list(gap_down) == [0.0, 0.0, 0.0, 1.0]


def test_range_discontinuity_respects_atr_warmup() -> None:
    period = 14
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(20):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(_bars(rows), period=period, source_id="range-discontinuity-warmup")

    gap_up = result.outputs[OutputId("gap_up_event")].values
    warmup_bars = period - 1
    assert result.warmup.warmup_bars == warmup_bars
    assert result.validity.valid_from_index == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(gap_up[index]) or gap_up[index] == 0.0


def test_range_discontinuity_warmup_is_at_least_two_bars() -> None:
    """Even with period=1 (ATR warmup 0), the component's own 2-bar lookback dominates."""
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.5),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 105.0, 112.0, 104.0, 110.0),
    ]
    result = _run(_bars(rows), period=1, source_id="range-discontinuity-min-warmup")
    assert result.warmup.warmup_bars == 2
    assert result.validity.valid_from_index == 2


@pytest.mark.parametrize("bar_count", [0, 1, 2])
def test_range_discontinuity_handles_fewer_than_three_bars(bar_count: int) -> None:
    all_rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.5),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 105.0, 112.0, 104.0, 110.0),
    ]
    if bar_count == 0:
        return  # AnalysisDataView requires at least one bar; nothing to assert.
    rows = all_rows[:bar_count]
    result = _run(_bars(rows), period=1, source_id=f"range-discontinuity-short-{bar_count}")
    gap_up = result.outputs[OutputId("gap_up_event")].values
    assert list(gap_up) == [0.0] * bar_count
