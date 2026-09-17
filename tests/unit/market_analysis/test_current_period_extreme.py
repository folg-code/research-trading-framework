"""Tests for the causal Session Current Period Extreme component."""

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
from trading_framework.market_analysis.components.session import CurrentPeriodExtremeComponent
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


def _run(*, side: str, source_id: str, period: str = "day") -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars())
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = CurrentPeriodExtremeComponent().parameter_schema.canonicalize(
        {"period": period, "side": side}
    )
    request = ComponentRequest(
        component_id=ComponentId("session.current_period_extreme"),
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
        if result.computation_identity.component_id.value == "session.current_period_extreme":
            return result
    raise AssertionError("session.current_period_extreme not computed")


def test_current_period_extreme_component_declares_shape() -> None:
    component = CurrentPeriodExtremeComponent()
    assert component.component_id.value == "session.current_period_extreme"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_current_period_high_is_a_running_max_that_resets_per_day() -> None:
    result = _run(side="high", source_id="current-high")
    values = result.outputs[OutputId("value")].values
    assert list(values) == [105.0, 110.0, 110.0, 107.0, 112.0]


def test_current_period_low_is_a_running_min_that_resets_per_day() -> None:
    result = _run(side="low", source_id="current-low")
    values = result.outputs[OutputId("value")].values
    assert list(values) == [95.0, 90.0, 90.0, 93.0, 85.0]


def test_current_period_week_does_not_reset_across_days_in_the_same_iso_week() -> None:
    """2024-06-03 (Mon) and 2024-06-04 (Tue) fall in the same ISO week -- unlike
    period="day", the running max must carry over instead of resetting."""
    result = _run(side="high", source_id="current-week", period="week")
    values = result.outputs[OutputId("value")].values
    assert list(values) == [105.0, 110.0, 110.0, 110.0, 112.0]


def test_current_period_extreme_never_reveals_a_later_bar_in_the_same_period() -> None:
    """Causal-boundary check: day 1's second bar (110 high) must not appear at
    day 1's first bar -- the running value only ever grows as bars arrive."""
    result = _run(side="high", source_id="current-causal")
    values = result.outputs[OutputId("value")].values
    assert values[0] == 105.0  # not yet aware of bar 2's 110 high
    assert values[1] == 110.0
