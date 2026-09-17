"""Tests for the causal Structure Close Reversal Level ("CISD") component."""

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
from trading_framework.market_analysis.components.structure import CloseReversalLevelComponent
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

_CLOSES = (100.0, 98.0, 99.0, 97.0)


def _bars(closes: tuple[float, ...]) -> list[MarketBar]:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, close in enumerate(closes):
        observed = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close + 1))),
                low=Price(Decimal(str(close - 1))),
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


def _run(closes: tuple[float, ...], *, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(closes))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = CloseReversalLevelComponent().parameter_schema.canonicalize({})
    request = ComponentRequest(
        component_id=ComponentId("structure.close_reversal_level"),
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
        if result.computation_identity.component_id.value == "structure.close_reversal_level":
            return result
    raise AssertionError("structure.close_reversal_level not computed")


def test_close_reversal_level_component_declares_shape() -> None:
    component = CloseReversalLevelComponent()
    assert component.component_id.value == "structure.close_reversal_level"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"reversal_event", "level"}


def test_close_reversal_level_flags_direction_reversals() -> None:
    result = _run(_CLOSES, source_id="close-reversal-flags")
    reversal_event = result.outputs[OutputId("reversal_event")].values
    level = result.outputs[OutputId("level")].values

    assert list(reversal_event) == [0.0, 0.0, 1.0, 1.0]
    assert np.isnan(level[0])
    assert np.isnan(level[1])
    assert level[2] == 100.0  # close two bars back from index 2
    assert level[3] == 98.0  # close two bars back from index 3


def test_close_reversal_level_ignores_a_continued_direction() -> None:
    # 100 -> 98 -> 96: both moves are down, no reversal.
    result = _run((100.0, 98.0, 96.0), source_id="close-reversal-continuation")
    reversal_event = result.outputs[OutputId("reversal_event")].values
    assert list(reversal_event) == [0.0, 0.0, 0.0]


def test_close_reversal_level_ignores_a_flat_bar() -> None:
    # 100 -> 98 -> 98: the second move is flat (direction 0), never a reversal.
    result = _run((100.0, 98.0, 98.0), source_id="close-reversal-flat")
    reversal_event = result.outputs[OutputId("reversal_event")].values
    assert list(reversal_event) == [0.0, 0.0, 0.0]
