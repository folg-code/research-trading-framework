"""Tests for the causal Structure Distance To Level component (IDEA-032, D-P19-03)."""

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
from trading_framework.market_analysis.components.structure import DistanceToLevelComponent
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

# Day 1 (pivot_range=1) confirms swing highs 110 (bar 1->2), 106 (bar 2->3,
# matches 110 within a generous tolerance), 115 (bar 4->5, matches 106); a
# swing low 100 (bar 0->2, nothing to match against). Day 1's running
# session ends at high=115, low=99. Day 2's first two bars sit inside that
# closed day's previous-high/low and extend the swing/matched-level chain.
_ROWS: tuple[tuple[datetime, float, float, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 100.0, 99.0, 100.0),
    (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 110.0, 100.0, 105.0),
    (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 105.0, 106.0, 104.0, 105.0),
    (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 103.0, 104.0, 102.0, 103.0),
    (datetime(2024, 6, 3, 13, 34, tzinfo=UTC), 103.0, 115.0, 103.0, 110.0),
    (datetime(2024, 6, 3, 13, 35, tzinfo=UTC), 110.0, 112.0, 109.0, 110.0),
    (datetime(2024, 6, 4, 13, 30, tzinfo=UTC), 110.0, 111.0, 109.0, 110.0),
    (datetime(2024, 6, 4, 13, 31, tzinfo=UTC), 110.0, 111.0, 108.0, 109.0),
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


def _run(
    rows: tuple[tuple[datetime, float, float, float, float], ...], *, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = DistanceToLevelComponent().parameter_schema.canonicalize(
        {"period": 1, "pivot_range": 1, "tolerance_atr_multiple": 1000.0}
    )
    request = ComponentRequest(
        component_id=ComponentId("structure.distance_to_level"),
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
        if result.computation_identity.component_id.value == "structure.distance_to_level":
            return result
    raise AssertionError("structure.distance_to_level not computed")


def test_distance_to_level_component_declares_shape() -> None:
    component = DistanceToLevelComponent()
    assert component.component_id.value == "structure.distance_to_level"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {
        "distance_to_session_high_atr",
        "distance_to_session_low_atr",
        "distance_to_previous_day_high_atr",
        "distance_to_previous_day_low_atr",
        "distance_to_matched_extreme_pair_high_atr",
        "distance_to_matched_extreme_pair_low_atr",
    }


def test_distance_to_level_matches_hand_computed_formula_on_day_two() -> None:
    result = _run(_ROWS, source_id="distance-to-level-hand-computed")
    outputs = result.outputs

    # Bar 6: close = 110.0, atr(period=1) = true_range = 2.0.
    close_6 = 110.0
    atr_6 = 2.0

    # Running session high/low as of bar 6 (day 2's own first bar): 111/109.
    session_high_6 = 111.0
    session_low_6 = 109.0
    assert outputs[OutputId("distance_to_session_high_atr")].values[6] == pytest.approx(
        (session_high_6 - close_6) / atr_6
    )
    assert outputs[OutputId("distance_to_session_low_atr")].values[6] == pytest.approx(
        (close_6 - session_low_6) / atr_6
    )

    # Day 1's fully-closed session high/low: 115/99.
    previous_day_high = 115.0
    previous_day_low = 99.0
    assert outputs[OutputId("distance_to_previous_day_high_atr")].values[6] == pytest.approx(
        (previous_day_high - close_6) / atr_6
    )
    assert outputs[OutputId("distance_to_previous_day_low_atr")].values[6] == pytest.approx(
        (close_6 - previous_day_low) / atr_6
    )

    # Latest matched swing high/low levels carried into bar 6: 112.0/109.0
    # (a new swing high at bar 6 itself, pivot=bar 5's high=112, matches the
    # prior 115 within the generous tolerance; the swing low similarly
    # carries 109.0 forward).
    matched_high_6 = 112.0
    matched_low_6 = 109.0
    assert outputs[OutputId("distance_to_matched_extreme_pair_high_atr")].values[
        6
    ] == pytest.approx((matched_high_6 - close_6) / atr_6)
    assert outputs[OutputId("distance_to_matched_extreme_pair_low_atr")].values[6] == pytest.approx(
        (close_6 - matched_low_6) / atr_6
    )


def test_distance_to_level_is_nan_before_a_level_exists() -> None:
    result = _run(_ROWS, source_id="distance-to-level-nan-before-level-exists")
    outputs = result.outputs
    # Day 1 has no previous day yet.
    previous_day_high = outputs[OutputId("distance_to_previous_day_high_atr")].values
    previous_day_low = outputs[OutputId("distance_to_previous_day_low_atr")].values
    for index in range(6):
        assert np.isnan(previous_day_high[index])
        assert np.isnan(previous_day_low[index])
    # Once day 2 starts, the previous day's high/low is available.
    assert not np.isnan(previous_day_high[6])
    assert not np.isnan(previous_day_low[6])


def test_distance_to_level_stays_nan_on_a_zero_atr_bar_with_no_level() -> None:
    rows = ((datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 100.0, 100.0, 100.0),)
    result = _run(rows, source_id="distance-to-level-zero-atr-no-level")
    outputs = result.outputs

    # A single flat bar: ATR is exactly 0.0, but there is no previous day
    # and no matched swing yet -- those distances must stay NaN, not
    # fabricate 0.0 just because the denominator happens to be zero.
    assert np.isnan(outputs[OutputId("distance_to_previous_day_high_atr")].values[0])
    assert np.isnan(outputs[OutputId("distance_to_previous_day_low_atr")].values[0])
    assert np.isnan(outputs[OutputId("distance_to_matched_extreme_pair_high_atr")].values[0])
    assert np.isnan(outputs[OutputId("distance_to_matched_extreme_pair_low_atr")].values[0])

    # The running session high/low DOES exist (it's just this one bar), so
    # the zero-ATR convention applies and these are 0.0, not NaN.
    assert outputs[OutputId("distance_to_session_high_atr")].values[0] == pytest.approx(0.0)
    assert outputs[OutputId("distance_to_session_low_atr")].values[0] == pytest.approx(0.0)
