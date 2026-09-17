"""Tests for the causal Structure Matched Extreme Pair ("equal highs/lows") component."""

from datetime import UTC, datetime
from decimal import Decimal

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
from trading_framework.market_analysis.components.structure import MatchedExtremePairComponent
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

# pivot_range=1: a swing high at p is confirmed at t=p+1 when high[t] <= high[p].
# Two peaks, at index 1 (high=110) and index 4 (high=115), each confirmed one
# bar later (index 2, index 5).
_ROWS: tuple[tuple[datetime, float, float, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 100.0, 99.0, 100.0),
    (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 110.0, 100.0, 105.0),
    (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 105.0, 106.0, 104.0, 105.0),
    (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 103.0, 104.0, 102.0, 103.0),
    (datetime(2024, 6, 3, 13, 34, tzinfo=UTC), 103.0, 115.0, 103.0, 110.0),
    (datetime(2024, 6, 3, 13, 35, tzinfo=UTC), 110.0, 112.0, 109.0, 110.0),
)


def _bars(rows: tuple[tuple[datetime, float, float, float, float], ...]) -> list[MarketBar]:
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


def _run(*, tolerance_atr_multiple: float, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(_ROWS))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = MatchedExtremePairComponent().parameter_schema.canonicalize(
        {"pivot_range": 1, "period": 1, "tolerance_atr_multiple": tolerance_atr_multiple}
    )
    request = ComponentRequest(
        component_id=ComponentId("structure.matched_extreme_pair"),
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
        if result.computation_identity.component_id.value == "structure.matched_extreme_pair":
            return result
    raise AssertionError("structure.matched_extreme_pair not computed")


def test_matched_extreme_pair_component_declares_shape() -> None:
    component = MatchedExtremePairComponent()
    assert component.component_id.value == "structure.matched_extreme_pair"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"matched_high_event", "matched_low_event"}


def test_first_swing_never_matches_and_second_matches_within_generous_tolerance() -> None:
    result = _run(tolerance_atr_multiple=1000.0, source_id="matched-generous-tolerance")
    matched_high = result.outputs[OutputId("matched_high_event")].values

    # Bar 2 confirms the first swing high (110): nothing to compare against yet.
    assert matched_high[2] == 0.0
    # Bar 5 confirms the second swing high (115): within a huge tolerance of 110.
    assert matched_high[5] == 1.0


def test_matched_extreme_pair_does_not_match_outside_tolerance() -> None:
    result = _run(tolerance_atr_multiple=0.0, source_id="matched-zero-tolerance")
    matched_high = result.outputs[OutputId("matched_high_event")].values

    # 115 vs 110 is a 5-point difference -- zero tolerance never matches.
    assert matched_high[5] == 0.0
