"""Tests for the causal Volatility Range Expansion component."""

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
from trading_framework.market_analysis.components.volatility import RangeExpansionComponent
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
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(bars)
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = RangeExpansionComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("volatility.range_expansion"),
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
        if result.computation_identity.component_id.value == "volatility.range_expansion":
            return result
    raise AssertionError("volatility.range_expansion not computed")


def test_range_expansion_component_declares_shape() -> None:
    component = RangeExpansionComponent()
    assert component.component_id.value == "volatility.range_expansion"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"ratio"}


def test_range_expansion_respects_atr_warmup() -> None:
    period = 5
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(15):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(_bars(rows), period=period, source_id="range-expansion-warmup")
    ratio = result.outputs[OutputId("ratio")].values

    warmup_bars = period - 1
    assert result.warmup.warmup_bars == warmup_bars
    assert result.validity.valid_from_index == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(ratio[index])
    for index in range(warmup_bars, len(ratio)):
        assert not np.isnan(ratio[index])


def test_range_expansion_zero_atr_is_defined_not_nan() -> None:
    # A perfectly flat instrument: true range and therefore ATR is exactly
    # 0.0 once warmup completes. The convention -- matching
    # trend.ema_distance's convention exactly -- is a defined 0.0, not an
    # incidental inf/NaN from dividing by zero.
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(10):
        stamp = start.replace(minute=start.minute + minute)
        rows.append((stamp, 100.0, 100.0, 100.0, 100.0))

    result = _run(_bars(rows), period=3, source_id="range-expansion-zero-atr")
    ratio = result.outputs[OutputId("ratio")].values

    warmup_bars = 3 - 1
    for index in range(warmup_bars, len(ratio)):
        assert ratio[index] == pytest.approx(0.0)


def test_range_expansion_hand_computed_ratio() -> None:
    # Hand-computed fixture: 6 bars, period=3. True range and ATR (SMA-of-TR)
    # values below were computed by hand from the Wilder true-range formula
    # (bar 0 uses close[0] as its own prior close) and the plain SMA:
    #
    #   bar   high    low    close   true_range
    #   0     101.0   99.0   100.0   2.0   (=high-low; prev_close=close[0])
    #   1     103.0   100.0  102.0   3.0   (=max(3, |103-100|, |100-100|))
    #   2     102.0   99.0   100.0   3.0   (=max(3, |102-102|, |99-102|))
    #   3     106.0   101.0  105.0   6.0   (=max(5, |106-100|, |101-100|))
    #   4     104.0   100.0  103.0   5.0   (=max(4, |104-105|, |100-105|))
    #   5     108.0   103.0  107.0   5.0   (=max(5, |108-103|, |103-103|))
    #
    #   atr[2] = mean(tr[0:3]) = (2+3+3)/3   = 8/3
    #   atr[3] = mean(tr[1:4]) = (3+3+6)/3   = 4
    #   atr[4] = mean(tr[2:5]) = (3+6+5)/3   = 14/3
    #   atr[5] = mean(tr[3:6]) = (6+5+5)/3   = 16/3
    #
    #   ratio[2] = tr[2] / atr[2] = 3 / (8/3)  = 9/8    = 1.125
    #   ratio[3] = tr[3] / atr[3] = 6 / 4      = 3/2    = 1.5
    #   ratio[4] = tr[4] / atr[4] = 5 / (14/3) = 15/14  ~= 1.0714285714285714
    #   ratio[5] = tr[5] / atr[5] = 5 / (16/3) = 15/16  = 0.9375
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = [
        (start.replace(minute=0), 100.0, 101.0, 99.0, 100.0),
        (start.replace(minute=1), 102.0, 103.0, 100.0, 102.0),
        (start.replace(minute=2), 100.0, 102.0, 99.0, 100.0),
        (start.replace(minute=3), 105.0, 106.0, 101.0, 105.0),
        (start.replace(minute=4), 103.0, 104.0, 100.0, 103.0),
        (start.replace(minute=5), 107.0, 108.0, 103.0, 107.0),
    ]

    result = _run(_bars(rows), period=3, source_id="range-expansion-hand-computed")
    ratio = result.outputs[OutputId("ratio")].values

    assert np.isnan(ratio[0])
    assert np.isnan(ratio[1])
    assert ratio[2] == pytest.approx(9.0 / 8.0)
    assert ratio[3] == pytest.approx(1.5)
    assert ratio[4] == pytest.approx(15.0 / 14.0)
    assert ratio[5] == pytest.approx(15.0 / 16.0)
