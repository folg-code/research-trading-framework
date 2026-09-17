"""Tests for the causal Session Previous Period Extreme component."""

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
from trading_framework.market_analysis.components.session import PreviousPeriodExtremeComponent
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

# Two NY trading days, three bars on day 1, two on day 2 (all EDT-summer, UTC-4).
# Day 1 final high/low = 110.0 / 90.0.
_ROWS: tuple[tuple[datetime, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 105.0, 95.0),
    (datetime(2024, 6, 3, 14, 30, tzinfo=UTC), 110.0, 90.0),
    (datetime(2024, 6, 3, 15, 30, tzinfo=UTC), 108.0, 92.0),
    (datetime(2024, 6, 4, 13, 30, tzinfo=UTC), 107.0, 93.0),
    (datetime(2024, 6, 4, 14, 30, tzinfo=UTC), 112.0, 85.0),
)


def _bars() -> list[MarketBar]:
    bars: list[MarketBar] = []
    for observed, high, low in _ROWS:
        bars.append(
            MarketBar(
                open=Price(Decimal(str(low))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(high))),
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


def _run(*, side: str, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars())
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = PreviousPeriodExtremeComponent().parameter_schema.canonicalize(
        {"period": "day", "side": side}
    )
    request = ComponentRequest(
        component_id=ComponentId("session.previous_period_extreme"),
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
        if result.computation_identity.component_id.value == "session.previous_period_extreme":
            return result
    raise AssertionError("session.previous_period_extreme not computed")


def test_previous_period_extreme_component_declares_shape() -> None:
    component = PreviousPeriodExtremeComponent()
    assert component.component_id.value == "session.previous_period_extreme"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_previous_period_high_is_nan_until_the_first_period_closes() -> None:
    result = _run(side="high", source_id="previous-high")
    values = result.outputs[OutputId("value")].values
    assert np.isnan(values[0])
    assert np.isnan(values[1])
    assert np.isnan(values[2])
    assert values[3] == 110.0
    assert values[4] == 110.0


def test_previous_period_low_holds_the_prior_days_final_low() -> None:
    result = _run(side="low", source_id="previous-low")
    values = result.outputs[OutputId("value")].values
    assert np.isnan(values[0])
    assert np.isnan(values[1])
    assert np.isnan(values[2])
    assert values[3] == 90.0
    assert values[4] == 90.0


def test_previous_period_extreme_never_leaks_the_still_open_current_period() -> None:
    """Causal-boundary check: day 2's own 112 high must never appear as
    'previous' during day 2 itself -- it only becomes 'previous' once day 2
    closes and day 3 begins (no day 3 exists in this fixture)."""
    result = _run(side="high", source_id="previous-causal")
    values = result.outputs[OutputId("value")].values
    assert values[3] != 112.0
    assert values[4] != 112.0
