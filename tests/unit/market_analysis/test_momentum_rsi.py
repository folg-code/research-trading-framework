"""Tests for the Wilder RSI momentum feature component (D-S051-03/04/05)."""

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    ComponentId,
    ComponentRequest,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.kernels import rsi_wilder
from trading_framework.market_analysis.components.momentum import RsiComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_momentum_rsi_component
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe


def _reference_rsi(closes: list[float], period: int) -> list[float]:
    """Independent, from-first-principles Wilder RSI -- never calls the kernel.

    Mirrors D-S051-05's exact recursion, coded separately from
    ``adapters/numpy/kernels.rsi_wilder`` so the test is a real check, not a
    tautology.
    """
    n = len(closes)
    out = [float("nan")] * n
    if n <= period or period < 2:
        return out
    diffs = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [d if d > 0 else 0.0 for d in diffs]
    losses = [-d if d < 0 else 0.0 for d in diffs]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi(avg_gain: float, avg_loss: float) -> float:
        if avg_gain == 0.0 and avg_loss == 0.0:
            return 50.0
        if avg_loss == 0.0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = _rsi(avg_gain, avg_loss)
    for i in range(period, len(diffs)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi(avg_gain, avg_loss)
    return out


def _bars(closes: list[float]) -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[MarketBar] = []
    for index, close in enumerate(closes):
        stamp = base.replace(hour=index // 60, minute=index % 60)
        available = (
            stamp.replace(minute=stamp.minute + 1)
            if stamp.minute < 59
            else (stamp.replace(hour=stamp.hour + 1, minute=0))
        )
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(close + 1))),
                low=Price(Decimal(str(close - 1))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=stamp,
                available_at=available,
            )
        )
    return bars


def _context(*, bar_count: int, source_id: str) -> AnalysisContext:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start.replace(minute=(bar_count - 1) % 60, hour=(bar_count - 1) // 60)
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
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


def _planning_context(*, bar_count: int) -> PlanningContext:
    context = _context(bar_count=bar_count, source_id="planning")
    return PlanningContext(
        dataset_ref=context.dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=context.requested_range,
    )


def _run_rsi(closes: list[float], *, period: int, source_id: str) -> np.ndarray:
    registry = ComponentRegistry()
    register_momentum_rsi_component(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("momentum.rsi"),
        parameters=RsiComponent().parameter_schema.canonicalize({"period": period}),
    )
    plan = planner.build_plan(
        _planning_context(bar_count=len(closes)),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(bar_count=len(closes), source_id=source_id),
    )
    assert len(workspace.result_store) == 1
    result = next(iter(workspace.result_store.results().values()))
    return np.asarray(result.outputs[OutputId("value")].values, dtype=np.float64)


# ---------------------------------------------------------------------------
# Kernel-level tests
# ---------------------------------------------------------------------------


def test_rsi_wilder_kernel_matches_independently_computed_reference() -> None:
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0, 108.0, 110.0]
    period = 3

    values = rsi_wilder(np.array(closes, dtype=np.float64), period)
    expected = _reference_rsi(closes, period)

    for index in range(len(closes)):
        if np.isnan(expected[index]):
            assert np.isnan(values[index])
        else:
            assert values[index] == pytest.approx(expected[index])


def test_rsi_wilder_kernel_warmup_is_nan_before_period() -> None:
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0]
    period = 3
    values = rsi_wilder(np.array(closes, dtype=np.float64), period)
    for index in range(period):
        assert np.isnan(values[index])
    assert not np.isnan(values[period])


def test_rsi_wilder_kernel_rejects_short_windows() -> None:
    close = np.array([100.0, 101.0], dtype=np.float64)
    assert np.all(np.isnan(rsi_wilder(close, 3)))
    assert np.all(np.isnan(rsi_wilder(close, 1)))


def test_rsi_wilder_monotonically_rising_series_gives_100() -> None:
    closes = np.array([100.0 + i for i in range(10)], dtype=np.float64)
    values = rsi_wilder(closes, 3)
    for index in range(3, len(closes)):
        assert values[index] == 100.0


def test_rsi_wilder_flat_series_gives_50() -> None:
    closes = np.full(10, 100.0, dtype=np.float64)
    values = rsi_wilder(closes, 3)
    for index in range(3, len(closes)):
        assert values[index] == 50.0


def test_rsi_wilder_kernel_is_causal() -> None:
    # Truncating the series after bar n must not change values at or before n.
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0, 108.0, 110.0]
    period = 3
    full = rsi_wilder(np.array(closes, dtype=np.float64), period)

    truncate_at = 7
    truncated = rsi_wilder(np.array(closes[: truncate_at + 1], dtype=np.float64), period)

    for index in range(truncate_at + 1):
        if np.isnan(full[index]):
            assert np.isnan(truncated[index])
        else:
            assert truncated[index] == pytest.approx(full[index])


# ---------------------------------------------------------------------------
# Component-level tests
# ---------------------------------------------------------------------------


def test_rsi_component_declares_shape() -> None:
    component = RsiComponent()
    assert component.component_id.value == "momentum.rsi"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_rsi_period_minimum_is_two() -> None:
    component = RsiComponent()
    with pytest.raises(ValidationError, match="period"):
        component.parameter_schema.canonicalize({"period": 1})


def test_rsi_component_depends_on_close_prices() -> None:
    component = RsiComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()


def test_rsi_component_history_requirement_covers_recursive_warmup() -> None:
    component = RsiComponent()
    parameters = component.parameter_schema.canonicalize({"period": 5})
    assert component.history_requirement(parameters).bars_before == 5


def test_executor_runs_rsi_component_matching_reference() -> None:
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0, 108.0, 110.0]
    period = 3

    values = _run_rsi(closes, period=period, source_id="rsi-reference")
    expected = _reference_rsi(closes, period)

    for index in range(len(closes)):
        if np.isnan(expected[index]):
            assert np.isnan(values[index])
        else:
            assert values[index] == pytest.approx(expected[index])


def test_rsi_component_valid_from_index_equals_period() -> None:
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0]
    period = 3

    registry = ComponentRegistry()
    register_momentum_rsi_component(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    request = ComponentRequest(
        component_id=ComponentId("momentum.rsi"),
        parameters=RsiComponent().parameter_schema.canonicalize({"period": period}),
    )
    plan = planner.build_plan(
        _planning_context(bar_count=len(closes)),
        [PlanningRequest.from_component_request(request)],
    )
    workspace = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=_context(bar_count=len(closes), source_id="rsi-warmup"),
    )
    result = next(iter(workspace.result_store.results().values()))
    values = np.asarray(result.outputs[OutputId("value")].values, dtype=np.float64)

    assert result.warmup.warmup_bars == period
    assert result.validity.valid_from_index == period
    for index in range(period):
        assert np.isnan(values[index])
    for index in range(period, len(closes)):
        assert not np.isnan(values[index])


def test_rsi_component_is_causal_when_truncated_after_bar_n() -> None:
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0, 108.0, 110.0]
    period = 3
    truncate_at = 7

    full = _run_rsi(closes, period=period, source_id="rsi-causal-full")
    truncated = _run_rsi(closes[: truncate_at + 1], period=period, source_id="rsi-causal-truncated")

    for index in range(truncate_at + 1):
        if np.isnan(full[index]):
            assert np.isnan(truncated[index])
        else:
            assert truncated[index] == pytest.approx(full[index])


def test_rsi_component_short_warmup_would_fail_this_test() -> None:
    # Guards against an off-by-one warm-up: if valid_from_index were
    # period - 1, this bar would incorrectly be treated as valid even though
    # the recursion has not yet consumed enough diffs to seed the averages.
    closes = [100.0, 102.0, 101.0, 103.0, 102.0, 105.0, 107.0, 106.0]
    period = 3

    values = _run_rsi(closes, period=period, source_id="rsi-warmup-off-by-one")
    assert np.isnan(values[period - 1])
    assert not np.isnan(values[period])
