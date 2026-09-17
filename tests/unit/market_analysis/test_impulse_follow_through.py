"""Tests for the retrospective Structure Impulse Follow-Through component."""

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
from trading_framework.market_analysis.components.structure import ImpulseFollowThroughComponent
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

# Same fixture as test_impulse_origin_range.py: bar 4 is the only impulsive
# bar (bullish, ATR(period=3)@bar4 ~= 12.667), bar 5 is its only follow-up bar.
_ROWS: tuple[tuple[datetime, float, float, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.0),
    (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 101.0, 99.0, 99.5),
    (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 99.5, 100.5, 98.5, 99.0),
    (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 99.0, 100.0, 97.0, 98.0),
    (datetime(2024, 6, 3, 13, 34, tzinfo=UTC), 98.0, 130.0, 97.0, 128.0),
    (datetime(2024, 6, 3, 13, 35, tzinfo=UTC), 128.0, 129.0, 90.0, 95.0),
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


def _run(*, lookahead_bars: int, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(_ROWS))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = ImpulseFollowThroughComponent().parameter_schema.canonicalize(
        {"period": 3, "lookahead_bars": lookahead_bars}
    )
    request = ComponentRequest(
        component_id=ComponentId("structure.impulse_follow_through"),
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
        if result.computation_identity.component_id.value == "structure.impulse_follow_through":
            return result
    raise AssertionError("structure.impulse_follow_through not computed")


def test_impulse_follow_through_component_declares_shape() -> None:
    component = ImpulseFollowThroughComponent()
    assert component.component_id.value == "structure.impulse_follow_through"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.RETROSPECTIVE
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"follow_through_atr"}


def test_impulse_follow_through_computes_atr_normalized_continuation() -> None:
    result = _run(lookahead_bars=1, source_id="follow-through-value")
    values = result.outputs[OutputId("follow_through_atr")].values

    # Bar 4 (bullish impulse): (high[5] - close[4]) / atr[4] = (129 - 128) / 12.667.
    assert values[4] == pytest.approx(1.0 / (38.0 / 3.0), rel=1e-6)


def test_impulse_follow_through_is_nan_on_non_impulsive_bars() -> None:
    result = _run(lookahead_bars=1, source_id="follow-through-non-impulsive")
    values = result.outputs[OutputId("follow_through_atr")].values
    for index in (0, 1, 2, 3):
        assert np.isnan(values[index])


def test_impulse_follow_through_is_nan_when_not_enough_future_bars() -> None:
    """Bar 5 is not impulsive here, but even if it were, lookahead_bars=1
    would need a bar 6 that does not exist -- the trailing edge is NaN,
    not a crash or a fabricated value."""
    result = _run(lookahead_bars=1, source_id="follow-through-trailing-edge")
    values = result.outputs[OutputId("follow_through_atr")].values
    assert np.isnan(values[5])


def test_impulse_follow_through_never_uses_more_than_the_configured_lookahead() -> None:
    """With lookahead_bars=2, bar 4 would need bar 6 (does not exist) --
    must be NaN, not silently computed from a shorter window."""
    result = _run(lookahead_bars=2, source_id="follow-through-lookahead-2")
    values = result.outputs[OutputId("follow_through_atr")].values
    assert np.isnan(values[4])
