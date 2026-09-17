"""Tests for the causal Structure Impulse Origin Range ("order block") component."""

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
from trading_framework.market_analysis.components.structure import ImpulseOriginRangeComponent
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

# Bars 0-2: quiet, small-range, to build a small ATR(period=3).
# Bar 3: bearish (the eventual origin candidate).
# Bar 4: huge bullish impulse (body 30 >= 1.5 * ATR(period=3)@bar4 ~= 19.0) --
#   confirms bar 3 as the active origin range.
# Bar 5: a big bearish bar (not itself impulsive) whose close (95) breaks
#   below the origin's low (97) -- invalidates the active range.
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


def _run(*, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(_ROWS))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = ImpulseOriginRangeComponent().parameter_schema.canonicalize({"period": 3})
    request = ComponentRequest(
        component_id=ComponentId("structure.impulse_origin_range"),
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
        if result.computation_identity.component_id.value == "structure.impulse_origin_range":
            return result
    raise AssertionError("structure.impulse_origin_range not computed")


def test_impulse_origin_range_component_declares_shape() -> None:
    component = ImpulseOriginRangeComponent()
    assert component.component_id.value == "structure.impulse_origin_range"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"origin_event", "origin_high", "origin_low", "role_active"}


def test_impulse_origin_range_confirms_the_opposite_direction_bar() -> None:
    result = _run(source_id="origin-confirm")
    origin_event = result.outputs[OutputId("origin_event")].values
    origin_high = result.outputs[OutputId("origin_high")].values
    origin_low = result.outputs[OutputId("origin_low")].values

    # Bar 4 confirms bar 3 (the bearish bar) as the origin range.
    assert origin_event[4] == 1.0
    assert origin_high[4] == 100.0  # bar 3's own high
    assert origin_low[4] == 97.0  # bar 3's own low
    assert origin_event[3] == 0.0  # the origin bar itself never fires the event


def test_impulse_origin_range_role_is_active_then_invalidated() -> None:
    result = _run(source_id="origin-role")
    role_active = result.outputs[OutputId("role_active")].values

    assert np.isnan(role_active[0])
    assert np.isnan(role_active[3])  # no origin confirmed yet
    assert role_active[4] == 1.0  # freshly confirmed, active
    assert role_active[5] == 0.0  # bar 5's close (95) breaks below origin_low (97)


def test_impulse_origin_range_state_is_forward_filled_while_active() -> None:
    result = _run(source_id="origin-forward-fill")
    origin_high = result.outputs[OutputId("origin_high")].values
    origin_low = result.outputs[OutputId("origin_low")].values

    # Bar 5's own values do not overwrite the still-recorded origin bounds.
    assert origin_high[5] == 100.0
    assert origin_low[5] == 97.0
