"""Tests for the causal Session Overlap Window component."""

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
from trading_framework.market_analysis.components.session import OverlapWindowComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import ComponentValidationError
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
from trading_framework.time.sessions import (
    CmeEsRthSessionResolver,
    GlobalSessionCalendarResolver,
    TradingSessionResolver,
)


def _bars(timestamps: list[datetime]) -> list[MarketBar]:
    bars: list[MarketBar] = []
    for observed in timestamps:
        price = Price(Decimal("100"))
        bars.append(
            MarketBar(
                open=price,
                high=price,
                low=price,
                close=price,
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
    timestamps: list[datetime],
    *,
    session_a: str,
    session_b: str,
    source_id: str,
    resolver: TradingSessionResolver | None = None,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(timestamps))
    resolver = resolver if resolver is not None else GlobalSessionCalendarResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = OverlapWindowComponent().parameter_schema.canonicalize(
        {"session_a": session_a, "session_b": session_b}
    )
    request = ComponentRequest(
        component_id=ComponentId("session.overlap_window"),
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
        if result.computation_identity.component_id.value == "session.overlap_window":
            return result
    raise AssertionError("session.overlap_window not computed")


def test_overlap_window_component_declares_shape() -> None:
    component = OverlapWindowComponent()
    assert component.component_id.value == "session.overlap_window"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"overlap"}


def test_overlap_window_flags_the_london_new_york_intersection() -> None:
    # Monday 2024-01-08 (winter, no DST): London 08:00-16:30 UTC+0,
    # New York 09:30-16:00 EST (UTC-5) -> 14:30-21:00 UTC.
    # Intersection: [14:30, 16:30) UTC.
    day = datetime(2024, 1, 8, tzinfo=UTC)
    timestamps = [
        day.replace(hour=7, minute=59),  # before both
        day.replace(hour=14, minute=29),  # London yes, NY not yet
        day.replace(hour=14, minute=30),  # overlap starts
        day.replace(hour=16, minute=0),  # inside overlap
        day.replace(hour=16, minute=29),  # inside overlap
        day.replace(hour=16, minute=30),  # London just closed -- overlap ends
    ]
    result = _run(timestamps, session_a="london", session_b="new_york", source_id="overlap-1")
    overlap = result.outputs[OutputId("overlap")].values
    assert list(overlap) == [0.0, 0.0, 1.0, 1.0, 1.0, 0.0]


def test_overlap_window_is_symmetric_in_its_two_parameters() -> None:
    day = datetime(2024, 1, 8, 15, 0, tzinfo=UTC)
    forward = _run([day], session_a="london", session_b="new_york", source_id="overlap-sym-1")
    backward = _run([day], session_a="new_york", session_b="london", source_id="overlap-sym-2")
    assert (
        forward.outputs[OutputId("overlap")].values == backward.outputs[OutputId("overlap")].values
    )


def test_overlap_window_rejects_unknown_session_name() -> None:
    with pytest.raises(ComponentValidationError, match="unknown session"):
        _run(
            [datetime(2024, 1, 8, 15, 0, tzinfo=UTC)],
            session_a="tokyo",
            session_b="london",
            source_id="overlap-invalid",
        )


def test_overlap_window_raises_component_error_when_resolver_lacks_named_sessions() -> None:
    """A resolver without session_* columns must surface as ComponentValidationError
    (naming this component), not the underlying generic ValidationError."""
    with pytest.raises(ComponentValidationError, match=r"session\.overlap_window"):
        _run(
            [datetime(2024, 1, 8, 15, 0, tzinfo=UTC)],
            session_a="london",
            session_b="new_york",
            source_id="overlap-plain-resolver",
            resolver=CmeEsRthSessionResolver(),
        )


def test_overlap_window_rejects_identical_session_names() -> None:
    with pytest.raises(ComponentValidationError, match="two different sessions"):
        _run(
            [datetime(2024, 1, 8, 15, 0, tzinfo=UTC)],
            session_a="london",
            session_b="london",
            source_id="overlap-same",
        )
