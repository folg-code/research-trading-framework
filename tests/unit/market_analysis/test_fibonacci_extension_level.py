"""Tests for the causal Structure Fibonacci Extension Level component (IDEA-032)."""

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
from trading_framework.market_analysis.components.structure import FibonacciExtensionLevelComponent
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

# Same fixture and swing structure as test_fibonacci_retracement_level.py /
# test_matched_extreme_pair.py.
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


def _run(*, ratio: float, source_id: str) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(_ROWS))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = FibonacciExtensionLevelComponent().parameter_schema.canonicalize(
        {"pivot_range": 1, "ratio": ratio}
    )
    request = ComponentRequest(
        component_id=ComponentId("structure.fibonacci_extension_level"),
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
        if result.computation_identity.component_id.value == "structure.fibonacci_extension_level":
            return result
    raise AssertionError("structure.fibonacci_extension_level not computed")


def test_fibonacci_extension_level_component_declares_shape() -> None:
    component = FibonacciExtensionLevelComponent()
    assert component.component_id.value == "structure.fibonacci_extension_level"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_fibonacci_extension_level_matches_hand_computed_formula() -> None:
    result = _run(ratio=2.0, source_id="fib-extension-hand-computed")
    value = result.outputs[OutputId("value")].values

    assert np.isnan(value[0])
    assert np.isnan(value[1])

    # index 2: down-leg. high=110, low=100, range=10.
    # value = high - ratio * range = 110 - 2.0*10 = 90.
    assert value[2] == pytest.approx(90.0)

    # index 3: up-leg. high=106, low=100, range=6.
    # value = low + ratio * range = 100 + 2.0*6 = 112.
    assert value[3] == pytest.approx(112.0)


def test_fibonacci_extension_level_respects_warmup() -> None:
    result = _run(ratio=2.0, source_id="fib-extension-warmup")
    value = result.outputs[OutputId("value")].values
    assert np.isnan(value[0])
    assert not np.isnan(value[2])
