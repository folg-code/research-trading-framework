"""Tests for the causal Candle Reversal Pattern component (D-P19-05)."""

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

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
from trading_framework.market_analysis.components.candle import ReversalPatternComponent
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

_NONE = 0.0
_ENGULFING = 1.0
_LEVEL_CLOSE_REVERSAL = 2.0
_REJECTION_WICK = 3.0


def _bars(rows: list[tuple[float, float, float, float]]) -> list[MarketBar]:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, (open_, high, low, close) in enumerate(rows):
        stamp = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
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


def _run(
    rows: list[tuple[float, float, float, float]], *, pivot_range: int, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = ReversalPatternComponent().parameter_schema.canonicalize(
        {"pivot_range": pivot_range}
    )
    request = ComponentRequest(
        component_id=ComponentId("candle.reversal_pattern"),
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
        if result.computation_identity.component_id.value == "candle.reversal_pattern":
            return result
    raise AssertionError("candle.reversal_pattern not computed")


def test_reversal_pattern_component_declares_shape() -> None:
    component = ReversalPatternComponent()
    assert component.component_id.value == "candle.reversal_pattern"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"bullish_pattern", "bearish_pattern"}


def test_reversal_pattern_detects_bullish_engulfing() -> None:
    # Bar 0 body [100, 102] (bearish). Bar 1 body [99, 104] (bullish) fully
    # contains it and closes the opposite direction -- bullish engulfing.
    rows = [
        (102.0, 103.0, 99.0, 100.0),
        (99.0, 105.0, 98.0, 104.0),
    ]
    result = _run(rows, pivot_range=2, source_id="reversal-engulfing")
    bullish = result.outputs[OutputId("bullish_pattern")].values
    bearish = result.outputs[OutputId("bearish_pattern")].values
    assert np.isnan(bullish[0])
    assert np.isnan(bearish[0])
    assert bullish[1] == _ENGULFING
    assert bearish[1] == _NONE


def test_reversal_pattern_detects_bullish_rejection_wick() -> None:
    # Bar 1: small bullish body [100.0, 100.3] with a long lower wick down
    # to 90.0 and a tiny upper wick -- a hammer-style bullish rejection.
    # Body does not contain bar 0's body, so engulfing does not apply.
    rows = [
        (100.0, 101.0, 99.0, 100.5),
        (100.0, 100.5, 90.0, 100.3),
    ]
    result = _run(rows, pivot_range=2, source_id="reversal-rejection-wick")
    bullish = result.outputs[OutputId("bullish_pattern")].values
    assert bullish[1] == _REJECTION_WICK


def test_reversal_pattern_detects_level_close_reversal_over_rejection_wick() -> None:
    # pivot_range=1: swing high at bar 1 (high=110) confirms at bar 2, same
    # setup as structure.level_sweep_rejection's own fixture. Bar 3 pierces
    # 110 (high=115) but closes back below it (108) -- a bearish
    # level_close_reversal. Bar 3 also happens to satisfy rejection_wick's
    # geometry, which demonstrates that level_close_reversal (priority 2)
    # wins over rejection_wick (priority 3).
    rows = [
        (100.0, 100.0, 99.0, 100.0),
        (100.0, 110.0, 100.0, 105.0),
        (105.0, 106.0, 104.0, 105.0),
        (105.0, 115.0, 104.0, 108.0),
    ]
    result = _run(rows, pivot_range=1, source_id="reversal-level-close-reversal")
    bearish = result.outputs[OutputId("bearish_pattern")].values
    assert bearish[3] == _LEVEL_CLOSE_REVERSAL


def test_reversal_pattern_labels_none_when_nothing_matches() -> None:
    rows = [
        (100.0, 101.0, 99.0, 100.5),
        (100.5, 101.2, 100.0, 101.0),
    ]
    result = _run(rows, pivot_range=2, source_id="reversal-none")
    bullish = result.outputs[OutputId("bullish_pattern")].values
    bearish = result.outputs[OutputId("bearish_pattern")].values
    assert bullish[1] == _NONE
    assert bearish[1] == _NONE


def test_reversal_pattern_respects_warmup() -> None:
    rows = [
        (100.0, 101.0, 99.0, 100.5),
        (100.5, 101.2, 100.0, 101.0),
    ]
    result = _run(rows, pivot_range=2, source_id="reversal-warmup")
    assert result.warmup.warmup_bars == 1
    bullish = result.outputs[OutputId("bullish_pattern")].values
    bearish = result.outputs[OutputId("bearish_pattern")].values
    assert np.isnan(bullish[0])
    assert np.isnan(bearish[0])
