"""Tests for the causal Volatility Directional Asymmetry component."""

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
from trading_framework.market_analysis.components.volatility import DirectionalAsymmetryComponent
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

_PARKINSON_CONSTANT = 1.0 / (4.0 * math.log(2.0))


def _bars(rows: list[tuple[datetime, float, float, float, float]]) -> list[MarketBar]:
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
    rows: list[tuple[datetime, float, float, float, float]], *, period: int, source_id: str
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = DirectionalAsymmetryComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("volatility.directional_asymmetry"),
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
        if result.computation_identity.component_id.value == "volatility.directional_asymmetry":
            return result
    raise AssertionError("volatility.directional_asymmetry not computed")


def test_directional_asymmetry_component_declares_shape() -> None:
    component = DirectionalAsymmetryComponent()
    assert component.component_id.value == "volatility.directional_asymmetry"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"up_volatility", "down_volatility", "asymmetry"}


def test_directional_asymmetry_matches_hand_computed_split() -> None:
    # Closes alternate up/down after bar 0: up, down, up, down.
    # Each bar's H/L ratio is chosen so ln(H/L) is exactly 2 (up bars) or 1
    # (down bars), giving per-bar Parkinson terms of 4*PC and 1*PC.
    closes = [100.0, 102.0, 101.0, 103.0, 99.0]
    ln_hl = [1.0, 2.0, 1.0, 2.0, 1.0]  # bar 0's ratio is unused (no prior close)
    lows = [95.0, 90.0, 95.0, 90.0, 95.0]
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute, (close, ratio, low) in enumerate(zip(closes, ln_hl, lows, strict=True)):
        high = low * math.exp(ratio)
        stamp = start.replace(minute=start.minute + minute)
        rows.append((stamp, close, high, low, close))

    result = _run(rows, period=3, source_id="asymmetry-hand-computed")
    up = result.outputs[OutputId("up_volatility")].values
    down = result.outputs[OutputId("down_volatility")].values
    asymmetry = result.outputs[OutputId("asymmetry")].values

    expected_up = math.sqrt(4.0 * _PARKINSON_CONSTANT)
    expected_down = math.sqrt(1.0 * _PARKINSON_CONSTANT)
    expected_asymmetry = math.log(expected_up / expected_down)

    for index in (2, 3, 4):
        assert up[index] == pytest.approx(expected_up)
        assert down[index] == pytest.approx(expected_down)
        assert asymmetry[index] == pytest.approx(expected_asymmetry)


def test_directional_asymmetry_respects_warmup() -> None:
    period = 3
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 105.0, 95.0, 100.0),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 102.0, 107.0, 97.0, 102.0),
        (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 101.0, 106.0, 96.0, 101.0),
    ]
    result = _run(rows, period=period, source_id="asymmetry-warmup")
    up = result.outputs[OutputId("up_volatility")].values
    assert result.warmup.warmup_bars == period - 1
    for index in range(period - 1):
        assert np.isnan(up[index])


def test_directional_asymmetry_is_nan_when_one_side_is_absent() -> None:
    # Strictly increasing closes: every bar in the window is "up", so
    # down_volatility (and therefore asymmetry) has no bars to average.
    period = 3
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(5):
        close = 100.0 + minute
        stamp = start.replace(minute=start.minute + minute)
        rows.append((stamp, close, close + 5.0, close - 5.0, close))

    result = _run(rows, period=period, source_id="asymmetry-one-sided")
    down = result.outputs[OutputId("down_volatility")].values
    asymmetry = result.outputs[OutputId("asymmetry")].values
    for index in range(period - 1, len(down)):
        assert np.isnan(down[index])
        assert np.isnan(asymmetry[index])
