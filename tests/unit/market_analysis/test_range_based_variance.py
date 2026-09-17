"""Tests for the causal Volatility Range-Based Variance component."""

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
from trading_framework.market_analysis.components.volatility import RangeBasedVarianceComponent
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
    rows: list[tuple[datetime, float, float, float, float]],
    *,
    period: int,
    method: str,
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = RangeBasedVarianceComponent().parameter_schema.canonicalize(
        {"period": period, "method": method}
    )
    request = ComponentRequest(
        component_id=ComponentId("volatility.range_based_variance"),
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
        if result.computation_identity.component_id.value == "volatility.range_based_variance":
            return result
    raise AssertionError("volatility.range_based_variance not computed")


def test_range_based_variance_component_declares_shape() -> None:
    component = RangeBasedVarianceComponent()
    assert component.component_id.value == "volatility.range_based_variance"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_parkinson_matches_hand_computed_formula_with_period_one() -> None:
    # H/L = e exactly, so ln(H/L) = 1 -> per-bar term = the Parkinson constant.
    low = 100.0
    high = low * math.e
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), low, high, low, low),
        (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), low, high, low, low),
    ]
    result = _run(rows, period=1, method="parkinson", source_id="pk-hand-computed")
    value = result.outputs[OutputId("value")].values
    assert value[0] == pytest.approx(math.sqrt(_PARKINSON_CONSTANT))
    assert value[1] == pytest.approx(math.sqrt(_PARKINSON_CONSTANT))


def test_range_based_variance_respects_warmup() -> None:
    period = 5
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(8):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.5))

    result = _run(rows, period=period, method="parkinson", source_id="pk-warmup")
    value = result.outputs[OutputId("value")].values
    warmup_bars = period - 1
    assert result.warmup.warmup_bars == warmup_bars
    for index in range(warmup_bars):
        assert np.isnan(value[index])
    for index in range(warmup_bars, len(value)):
        assert not np.isnan(value[index])
        assert value[index] >= 0.0


def test_garman_klass_produces_non_negative_finite_values() -> None:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    rows = []
    for minute in range(5):
        stamp = start.replace(minute=start.minute + minute)
        base = 100.0 + minute
        rows.append((stamp, base, base + 2.0, base - 2.0, base + 0.3))

    result = _run(rows, period=3, method="garman_klass", source_id="gk-sanity")
    value = result.outputs[OutputId("value")].values
    for index in range(2, len(value)):
        assert not np.isnan(value[index])
        assert value[index] >= 0.0
        assert np.isfinite(value[index])


def test_range_based_variance_rejects_unknown_method() -> None:
    rows = [
        (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 101.0, 99.0, 100.0),
    ]
    with pytest.raises(ComponentValidationError, match="unknown method"):
        _run(rows, period=1, method="bollinger", source_id="pk-invalid-method")
