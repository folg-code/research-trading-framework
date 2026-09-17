"""Tests for the causal Volatility Regime State component."""

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
from trading_framework.market_analysis.components.volatility import RegimeStateComponent
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


def _bars(ranges: list[float]) -> list[MarketBar]:
    # close == open == 100.0 for every bar, so true_range == the bar's own
    # range exactly: TR = max(H-L, |H-100|, |L-100|) = max(r, r/2, r/2) = r.
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    bars: list[MarketBar] = []
    for minute, r in enumerate(ranges):
        stamp = start.replace(minute=start.minute + minute)
        bars.append(
            MarketBar(
                open=Price(Decimal("100")),
                high=Price(Decimal(str(100.0 + r / 2.0))),
                low=Price(Decimal(str(100.0 - r / 2.0))),
                close=Price(Decimal("100")),
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
    ranges: list[float],
    *,
    fast_period: int,
    slow_period: int,
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(ranges))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = RegimeStateComponent().parameter_schema.canonicalize(
        {"fast_period": fast_period, "slow_period": slow_period}
    )
    request = ComponentRequest(
        component_id=ComponentId("volatility.regime_state"),
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
        if result.computation_identity.component_id.value == "volatility.regime_state":
            return result
    raise AssertionError("volatility.regime_state not computed")


def test_regime_state_component_declares_shape() -> None:
    component = RegimeStateComponent()
    assert component.component_id.value == "volatility.regime_state"
    assert component.kind is ComponentKind.STATE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"state", "ratio"}


def test_regime_state_detects_compression() -> None:
    # TR drops from 4.0 to 2.0 partway through: at the last bar, fast ATR(2)
    # = 2.0 (both recent bars low) while slow ATR(4) = avg(4,4,2,2) = 3.0.
    # ratio = 2/3 ~= 0.667, below the default 0.85 compression threshold.
    ranges = [4.0, 4.0, 4.0, 4.0, 4.0, 4.0, 2.0, 2.0]
    result = _run(ranges, fast_period=2, slow_period=4, source_id="regime-compression")
    state = result.outputs[OutputId("state")].values
    ratio = result.outputs[OutputId("ratio")].values
    assert ratio[-1] == pytest.approx(2.0 / 3.0)
    assert state[-1] == pytest.approx(-1.0)


def test_regime_state_detects_expansion() -> None:
    # Mirror image: TR rises from 2.0 to 4.0. fast ATR(2) = 4.0, slow
    # ATR(4) = avg(2,2,4,4) = 3.0. ratio = 4/3 ~= 1.333, above the default
    # 1.15 expansion threshold.
    ranges = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 4.0, 4.0]
    result = _run(ranges, fast_period=2, slow_period=4, source_id="regime-expansion")
    state = result.outputs[OutputId("state")].values
    ratio = result.outputs[OutputId("ratio")].values
    assert ratio[-1] == pytest.approx(4.0 / 3.0)
    assert state[-1] == pytest.approx(1.0)


def test_regime_state_is_balanced_for_constant_volatility() -> None:
    ranges = [3.0] * 6
    result = _run(ranges, fast_period=2, slow_period=4, source_id="regime-balanced")
    state = result.outputs[OutputId("state")].values
    ratio = result.outputs[OutputId("ratio")].values
    assert ratio[-1] == pytest.approx(1.0)
    assert state[-1] == pytest.approx(0.0)


def test_regime_state_zero_denominator_reads_as_compression() -> None:
    # A perfectly flat window makes both fast and slow ATR exactly 0.0.
    ranges = [0.0] * 6
    result = _run(ranges, fast_period=2, slow_period=4, source_id="regime-flat")
    state = result.outputs[OutputId("state")].values
    ratio = result.outputs[OutputId("ratio")].values
    assert ratio[-1] == pytest.approx(0.0)
    assert state[-1] == pytest.approx(-1.0)


def test_regime_state_respects_warmup() -> None:
    ranges = [3.0] * 6
    result = _run(ranges, fast_period=2, slow_period=4, source_id="regime-warmup")
    state = result.outputs[OutputId("state")].values
    warmup_bars = 4 - 1
    assert result.warmup.warmup_bars == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(state[index])
    for index in range(warmup_bars, len(state)):
        assert not np.isnan(state[index])


def test_regime_state_rejects_fast_period_not_less_than_slow_period() -> None:
    ranges = [3.0] * 6
    with pytest.raises(ComponentValidationError, match="must be less than"):
        _run(ranges, fast_period=4, slow_period=4, source_id="regime-invalid-periods")
