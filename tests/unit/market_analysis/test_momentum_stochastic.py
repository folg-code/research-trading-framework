"""Tests for the Stochastic Oscillator momentum feature component (D-S051-03/04)."""

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
    ComponentRequest,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.kernels import (
    rolling_max,
    rolling_min,
    stochastic_percent_k,
)
from trading_framework.market_analysis.components.momentum import StochasticComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import (
    register_momentum_stochastic_component,
)
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe


def _reference_percent_k(
    high: list[float], low: list[float], close: list[float], period: int
) -> list[float]:
    """Independent, from-first-principles %K -- never calls the kernel."""
    n = len(close)
    out = [float("nan")] * n
    for index in range(period - 1, n):
        window_low = min(low[index - period + 1 : index + 1])
        window_high = max(high[index - period + 1 : index + 1])
        denominator = window_high - window_low
        if denominator == 0.0:
            out[index] = 50.0
        else:
            out[index] = (close[index] - window_low) / denominator * 100.0
    return out


def _reference_sma(values: list[float], period: int) -> list[float]:
    n = len(values)
    out = [float("nan")] * n
    for index in range(period - 1, n):
        window = values[index - period + 1 : index + 1]
        out[index] = sum(window) / period
    return out


def _bars(highs: list[float], lows: list[float], closes: list[float]) -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[MarketBar] = []
    for index, (high, low, close) in enumerate(zip(highs, lows, closes, strict=True)):
        stamp = base.replace(hour=index // 60, minute=index % 60)
        available = (
            stamp.replace(minute=stamp.minute + 1)
            if stamp.minute < 59
            else (stamp.replace(hour=stamp.hour + 1, minute=0))
        )
        bars.append(
            MarketBar(
                open=Price(Decimal(str(close))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
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


def _run_stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    period: int,
    smoothing_period: int,
    source_id: str,
) -> AnalysisResult:
    registry = ComponentRegistry()
    register_momentum_stochastic_component(registry)
    view = AnalysisDataView.from_bars(_bars(highs, lows, closes))
    planner = DependencyPlanner(registry)
    parameters = StochasticComponent().parameter_schema.canonicalize(
        {"period": period, "smoothing_period": smoothing_period}
    )
    request = ComponentRequest(
        component_id=ComponentId("momentum.stochastic"),
        parameters=parameters,
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
    return next(iter(workspace.result_store.results().values()))


_HIGHS = [
    101.0,
    103.0,
    102.0,
    104.0,
    105.0,
    104.5,
    106.0,
    107.0,
    106.5,
    108.0,
    109.0,
    108.5,
    110.0,
    111.0,
    110.5,
    112.0,
    113.0,
    112.5,
    114.0,
    115.0,
]
_LOWS = [
    99.0,
    101.0,
    100.0,
    102.0,
    103.0,
    102.5,
    104.0,
    105.0,
    104.5,
    106.0,
    107.0,
    106.5,
    108.0,
    109.0,
    108.5,
    110.0,
    111.0,
    110.5,
    112.0,
    113.0,
]
_CLOSES = [
    100.0,
    102.0,
    101.0,
    103.0,
    104.0,
    103.5,
    105.0,
    106.0,
    105.5,
    107.0,
    108.0,
    107.5,
    109.0,
    110.0,
    109.5,
    111.0,
    112.0,
    111.5,
    113.0,
    114.0,
]


# ---------------------------------------------------------------------------
# Kernel-level tests
# ---------------------------------------------------------------------------


def test_rolling_min_matches_independently_computed_reference() -> None:
    period = 3
    values = rolling_min(np.array(_LOWS, dtype=np.float64), period)
    for index in range(len(_LOWS)):
        if index < period - 1:
            assert np.isnan(values[index])
        else:
            expected = min(_LOWS[index - period + 1 : index + 1])
            assert values[index] == pytest.approx(expected)


def test_rolling_max_matches_independently_computed_reference() -> None:
    period = 3
    values = rolling_max(np.array(_HIGHS, dtype=np.float64), period)
    for index in range(len(_HIGHS)):
        if index < period - 1:
            assert np.isnan(values[index])
        else:
            expected = max(_HIGHS[index - period + 1 : index + 1])
            assert values[index] == pytest.approx(expected)


def test_stochastic_percent_k_kernel_matches_independently_computed_reference() -> None:
    period = 5
    high = np.array(_HIGHS, dtype=np.float64)
    low = np.array(_LOWS, dtype=np.float64)
    close = np.array(_CLOSES, dtype=np.float64)

    values = stochastic_percent_k(high, low, close, period)
    expected = _reference_percent_k(_HIGHS, _LOWS, _CLOSES, period)

    for index in range(len(_CLOSES)):
        if np.isnan(expected[index]):
            assert np.isnan(values[index])
        else:
            assert values[index] == pytest.approx(expected[index])


def test_stochastic_percent_k_kernel_zero_range_window_yields_fifty_not_zero() -> None:
    # A genuinely flat window (every bar's high/low identical) -- D-S051-04:
    # 50.0 (the neutral midpoint), NOT 0.0, so a flat window is never
    # confused with the real "close at the window low" signal (%K == 0.0).
    period = 3
    high = np.full(6, 100.0, dtype=np.float64)
    low = np.full(6, 100.0, dtype=np.float64)
    close = np.full(6, 100.0, dtype=np.float64)

    values = stochastic_percent_k(high, low, close, period)

    for index in range(period - 1, 6):
        assert values[index] == 50.0


def test_stochastic_percent_k_kernel_is_causal() -> None:
    period = 5
    high = np.array(_HIGHS, dtype=np.float64)
    low = np.array(_LOWS, dtype=np.float64)
    close = np.array(_CLOSES, dtype=np.float64)
    full = stochastic_percent_k(high, low, close, period)

    truncate_at = 12
    truncated = stochastic_percent_k(
        high[: truncate_at + 1], low[: truncate_at + 1], close[: truncate_at + 1], period
    )

    for index in range(truncate_at + 1):
        if np.isnan(full[index]):
            assert np.isnan(truncated[index])
        else:
            assert truncated[index] == pytest.approx(full[index])


# ---------------------------------------------------------------------------
# Component-level shape / dependency-declaration tests
# ---------------------------------------------------------------------------


def test_stochastic_component_declares_shape() -> None:
    component = StochasticComponent()
    assert component.component_id.value == "momentum.stochastic"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"k", "d"}


def test_stochastic_component_depends_on_high_low_close() -> None:
    component = StochasticComponent()
    parameters = component.parameter_schema.canonicalize({"period": 14, "smoothing_period": 3})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"high", "low", "close"}
    assert component.component_dependencies(parameters) == ()


def test_stochastic_component_history_requirement_covers_both_windows() -> None:
    component = StochasticComponent()
    parameters = component.parameter_schema.canonicalize({"period": 5, "smoothing_period": 4})
    assert component.history_requirement(parameters).bars_before == 5 + 4 - 2


# ---------------------------------------------------------------------------
# Value-correctness / warm-up / degenerate-window / causality tests
# ---------------------------------------------------------------------------


def test_stochastic_k_matches_independently_computed_rolling_high_low_range() -> None:
    period, smoothing_period = 5, 3
    result = _run_stochastic(
        _HIGHS,
        _LOWS,
        _CLOSES,
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-k",
    )
    k = np.asarray(result.outputs[OutputId("k")].values, dtype=np.float64)
    expected_k = _reference_percent_k(_HIGHS, _LOWS, _CLOSES, period)

    for index in range(len(_CLOSES)):
        if np.isnan(expected_k[index]):
            assert np.isnan(k[index])
        else:
            assert k[index] == pytest.approx(expected_k[index])


def test_stochastic_d_is_sma_of_k_over_smoothing_period() -> None:
    period, smoothing_period = 5, 3
    result = _run_stochastic(
        _HIGHS,
        _LOWS,
        _CLOSES,
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-d",
    )
    k = np.asarray(result.outputs[OutputId("k")].values, dtype=np.float64)
    d = np.asarray(result.outputs[OutputId("d")].values, dtype=np.float64)

    expected_k = _reference_percent_k(_HIGHS, _LOWS, _CLOSES, period)
    expected_d = _reference_sma(expected_k, smoothing_period)

    for index in range(len(_CLOSES)):
        assert np.isnan(k[index]) == np.isnan(expected_k[index])
        if np.isnan(expected_d[index]):
            assert np.isnan(d[index])
        else:
            assert d[index] == pytest.approx(expected_d[index])


def test_stochastic_zero_range_window_yields_fifty_not_zero() -> None:
    period, smoothing_period = 3, 2
    highs = [100.0] * 8
    lows = [100.0] * 8
    closes = [100.0] * 8

    result = _run_stochastic(
        highs,
        lows,
        closes,
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-zero-range",
    )
    k = np.asarray(result.outputs[OutputId("k")].values, dtype=np.float64)
    d = np.asarray(result.outputs[OutputId("d")].values, dtype=np.float64)

    warmup = period + smoothing_period - 2
    for index in range(warmup, len(closes)):
        assert k[index] == 50.0
        assert d[index] == 50.0


def test_stochastic_warmup_covers_rolling_window_plus_smoothing_window() -> None:
    period, smoothing_period = 5, 3
    result = _run_stochastic(
        _HIGHS,
        _LOWS,
        _CLOSES,
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-warmup",
    )
    k = np.asarray(result.outputs[OutputId("k")].values, dtype=np.float64)
    d = np.asarray(result.outputs[OutputId("d")].values, dtype=np.float64)

    expected_warmup = period + smoothing_period - 2
    assert result.warmup.warmup_bars == expected_warmup
    assert result.validity.valid_from_index == expected_warmup

    for index in range(expected_warmup):
        assert np.isnan(d[index])
    for index in range(expected_warmup, len(_CLOSES)):
        assert not np.isnan(k[index])
        assert not np.isnan(d[index])


def test_stochastic_component_is_causal_when_truncated_after_bar_n() -> None:
    period, smoothing_period = 5, 3
    truncate_at = 14

    full = _run_stochastic(
        _HIGHS,
        _LOWS,
        _CLOSES,
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-causal-full",
    )
    truncated = _run_stochastic(
        _HIGHS[: truncate_at + 1],
        _LOWS[: truncate_at + 1],
        _CLOSES[: truncate_at + 1],
        period=period,
        smoothing_period=smoothing_period,
        source_id="stochastic-causal-truncated",
    )

    for output_id in ("k", "d"):
        full_values = np.asarray(full.outputs[OutputId(output_id)].values, dtype=np.float64)
        truncated_values = np.asarray(
            truncated.outputs[OutputId(output_id)].values, dtype=np.float64
        )
        for index in range(truncate_at + 1):
            if np.isnan(full_values[index]):
                assert np.isnan(truncated_values[index])
            else:
                assert truncated_values[index] == pytest.approx(full_values[index])
