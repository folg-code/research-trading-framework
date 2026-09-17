"""Tests for the causal Statistics Rolling Window Position component (IDEA-030)."""

import math
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
from trading_framework.market_analysis.components.statistics import RollingWindowPositionComponent
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
from trading_framework.time.sessions import CmeEsRthSessionResolver

# ATR(source_period=1) == true range directly. Hand-computed TR sequence
# (bar 0 uses its own close as prior close, per true_range's convention):
# TR = [2, 5, 3, 3, 5].
_ROWS: list[tuple[float, float, float, float]] = [
    (100.0, 101.0, 99.0, 100.0),
    (100.0, 105.0, 100.0, 103.0),
    (103.0, 104.0, 101.0, 102.0),
    (102.0, 103.0, 100.0, 101.0),
    (103.0, 106.0, 101.0, 105.0),
]


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
    rows: list[tuple[float, float, float, float]],
    *,
    window: int,
    method: str,
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = RollingWindowPositionComponent().parameter_schema.canonicalize(
        {"source_period": 1, "window": window, "method": method}
    )
    request = ComponentRequest(
        component_id=ComponentId("statistics.rolling_window_position"),
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
        if result.computation_identity.component_id.value == "statistics.rolling_window_position":
            return result
    raise AssertionError("statistics.rolling_window_position not computed")


def test_rolling_window_position_component_declares_shape() -> None:
    component = RollingWindowPositionComponent()
    assert component.component_id.value == "statistics.rolling_window_position"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"z_score", "percentile"}


def test_rolling_window_position_matches_hand_computed_normal_method() -> None:
    result = _run(_ROWS, window=3, method="normal", source_id="rwp-normal")
    z_score = result.outputs[OutputId("z_score")].values
    percentile = result.outputs[OutputId("percentile")].values

    # index 2: window TR = [2, 5, 3], mean = 10/3, population stdev = sqrt(1.5556).
    mean_2 = 10.0 / 3.0
    stdev_2 = math.sqrt(((2 - mean_2) ** 2 + (5 - mean_2) ** 2 + (3 - mean_2) ** 2) / 3.0)
    expected_z_2 = (3.0 - mean_2) / stdev_2
    expected_percentile_2 = 0.5 * (1.0 + math.erf(expected_z_2 / math.sqrt(2.0)))
    assert z_score[2] == pytest.approx(expected_z_2)
    assert percentile[2] == pytest.approx(expected_percentile_2)


def test_rolling_window_position_matches_hand_computed_empirical_method() -> None:
    result = _run(_ROWS, window=3, method="empirical", source_id="rwp-empirical")
    percentile = result.outputs[OutputId("percentile")].values

    # index 2: window TR = [2, 5, 3], current = 3 -> 2 of 3 values <= 3.
    assert percentile[2] == pytest.approx(2.0 / 3.0)
    # index 3: window TR = [5, 3, 3], current = 3 -> 2 of 3 values <= 3.
    assert percentile[3] == pytest.approx(2.0 / 3.0)
    # index 4: window TR = [3, 3, 5], current = 5 -> 3 of 3 values <= 5.
    assert percentile[4] == pytest.approx(1.0)


def test_rolling_window_position_is_zero_for_a_flat_window() -> None:
    # close == open == 100.0 for every bar makes TR == the bar's own range
    # exactly (see the volatility.regime_state tests for the same trick).
    rows = [(100.0, 100.0 + r / 2.0, 100.0 - r / 2.0, 100.0) for r in [4.0, 4.0, 4.0, 4.0, 4.0]]
    result = _run(rows, window=3, method="normal", source_id="rwp-flat")
    z_score = result.outputs[OutputId("z_score")].values
    percentile = result.outputs[OutputId("percentile")].values
    assert z_score[2] == pytest.approx(0.0)
    assert percentile[2] == pytest.approx(0.5)


def test_rolling_window_position_respects_warmup() -> None:
    window = 3
    result = _run(_ROWS, window=window, method="normal", source_id="rwp-warmup")
    z_score = result.outputs[OutputId("z_score")].values
    assert result.warmup.warmup_bars == window - 1
    for index in range(window - 1):
        assert np.isnan(z_score[index])
    for index in range(window - 1, len(z_score)):
        assert not np.isnan(z_score[index])


def test_rolling_window_position_rejects_unknown_method() -> None:
    with pytest.raises(ComponentValidationError, match="unknown method"):
        _run(_ROWS, window=3, method="bogus", source_id="rwp-invalid-method")
