"""Tests for the MACD momentum feature component (D-S051-03/05, Finding 4)."""

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
from trading_framework.market_analysis.adapters.numpy.kernels import ema
from trading_framework.market_analysis.components.momentum import MacdComponent
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


def _run_macd(
    closes: list[float],
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
    source_id: str,
) -> AnalysisResult:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    parameters = MacdComponent().parameter_schema.canonicalize(
        {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
        }
    )
    request = ComponentRequest(
        component_id=ComponentId("momentum.macd"),
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
    for result in workspace.result_store.results().values():
        if result.computation_identity.component_id.value == "momentum.macd":
            return result
    raise AssertionError("momentum.macd not computed")


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
# Component-level shape / dependency-declaration tests
# ---------------------------------------------------------------------------


def test_macd_component_declares_shape() -> None:
    component = MacdComponent()
    assert component.component_id.value == "momentum.macd"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"line", "signal", "histogram"}


def test_macd_component_depends_on_two_ema_outputs_not_raw_close() -> None:
    component = MacdComponent()
    parameters = component.parameter_schema.canonicalize(
        {"fast_period": 12, "slow_period": 26, "signal_period": 9}
    )
    assert component.data_dependencies(parameters) == ()

    dependencies = component.component_dependencies(parameters)
    assert len(dependencies) == 2
    component_ids = {dependency.output_ref.component_id.value for dependency in dependencies}
    assert component_ids == {"trend.ema"}
    periods = {dependency.output_ref.parameters.get("period") for dependency in dependencies}
    assert periods == {12, 26}
    output_ids = {dependency.output_ref.output_id.value for dependency in dependencies}
    assert output_ids == {"value"}


def test_macd_rejects_fast_period_not_less_than_slow_period() -> None:
    component = MacdComponent()
    parameters = component.parameter_schema.canonicalize(
        {"fast_period": 26, "slow_period": 26, "signal_period": 9}
    )
    with pytest.raises(ComponentValidationError) as excinfo:
        component.component_dependencies(parameters)
    message = str(excinfo.value)
    assert "26" in message

    parameters = component.parameter_schema.canonicalize(
        {"fast_period": 30, "slow_period": 12, "signal_period": 9}
    )
    with pytest.raises(ComponentValidationError) as excinfo:
        component.component_dependencies(parameters)
    message = str(excinfo.value)
    assert "30" in message
    assert "12" in message


# ---------------------------------------------------------------------------
# Planner / DAG test -- the acceptance criterion this task adds beyond RSI's
# ---------------------------------------------------------------------------


def test_macd_dependency_declaration_resolves_through_the_planner_dag() -> None:
    fast_period = 5
    slow_period = 8
    signal_period = 3
    bar_count = 20

    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = MacdComponent().parameter_schema.canonicalize(
        {"fast_period": fast_period, "slow_period": slow_period, "signal_period": signal_period}
    )
    request = ComponentRequest(component_id=ComponentId("momentum.macd"), parameters=parameters)
    plan = planner.build_plan(
        _planning_context(bar_count=bar_count),
        [PlanningRequest.from_component_request(request)],
    )

    component_nodes = plan.component_nodes()
    ema_nodes = [
        node for node in component_nodes if node.component.component_id.value == "trend.ema"
    ]
    macd_nodes = [
        node for node in component_nodes if node.component.component_id.value == "momentum.macd"
    ]

    # Same component (trend.ema), two distinct parameter sets -> two distinct
    # planned nodes with distinct cache keys (canonical_key()), not one node
    # reused twice.
    assert len(ema_nodes) == 2
    assert len(macd_nodes) == 1
    ema_periods = {node.request.parameters.get("period") for node in ema_nodes}
    assert ema_periods == {fast_period, slow_period}
    ema_keys = {node.computation_identity.canonical_key() for node in ema_nodes}
    assert len(ema_keys) == 2

    macd_node = macd_nodes[0]
    assert set(macd_node.dependency_keys) == ema_keys

    # The DAG places both trend.ema nodes strictly before momentum.macd.
    ordered_ids = [node.component.component_id.value for node in component_nodes]
    macd_index = ordered_ids.index("momentum.macd")
    assert all(
        ordered_ids.index(node.component.component_id.value) < macd_index for node in ema_nodes
    )


# ---------------------------------------------------------------------------
# Value-correctness / warm-up / causality tests
# ---------------------------------------------------------------------------


def test_macd_line_equals_difference_of_the_two_ema_dependencies_bar_for_bar() -> None:
    fast_period, slow_period, signal_period = 3, 6, 3
    result = _run_macd(
        _CLOSES,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-line",
    )
    line = np.asarray(result.outputs[OutputId("line")].values, dtype=np.float64)

    close = np.array(_CLOSES, dtype=np.float64)
    expected_line = ema(close, fast_period) - ema(close, slow_period)

    for index in range(len(_CLOSES)):
        if np.isnan(expected_line[index]):
            assert np.isnan(line[index])
        else:
            assert line[index] == pytest.approx(expected_line[index])


def test_macd_signal_equals_shared_ema_kernel_applied_to_line() -> None:
    fast_period, slow_period, signal_period = 3, 6, 3
    result = _run_macd(
        _CLOSES,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-signal",
    )
    signal = np.asarray(result.outputs[OutputId("signal")].values, dtype=np.float64)

    close = np.array(_CLOSES, dtype=np.float64)
    expected_line = ema(close, fast_period) - ema(close, slow_period)
    line_valid_from = slow_period - 1
    expected_signal_segment = ema(expected_line[line_valid_from:], signal_period)

    for offset, expected in enumerate(expected_signal_segment):
        index = line_valid_from + offset
        if np.isnan(expected):
            assert np.isnan(signal[index])
        else:
            assert signal[index] == pytest.approx(expected)


def test_macd_histogram_equals_line_minus_signal_exactly() -> None:
    fast_period, slow_period, signal_period = 3, 6, 3
    result = _run_macd(
        _CLOSES,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-histogram",
    )
    line = np.asarray(result.outputs[OutputId("line")].values, dtype=np.float64)
    signal = np.asarray(result.outputs[OutputId("signal")].values, dtype=np.float64)
    histogram = np.asarray(result.outputs[OutputId("histogram")].values, dtype=np.float64)

    for index in range(len(_CLOSES)):
        if np.isnan(line[index]) or np.isnan(signal[index]):
            assert np.isnan(histogram[index])
        else:
            assert histogram[index] == line[index] - signal[index]


def test_macd_warmup_is_slow_ema_warmup_plus_signal_ema_warmup() -> None:
    fast_period, slow_period, signal_period = 3, 6, 3
    result = _run_macd(
        _CLOSES,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-warmup",
    )
    line = np.asarray(result.outputs[OutputId("line")].values, dtype=np.float64)
    signal = np.asarray(result.outputs[OutputId("signal")].values, dtype=np.float64)
    histogram = np.asarray(result.outputs[OutputId("histogram")].values, dtype=np.float64)

    expected_warmup = (slow_period - 1) + (signal_period - 1)
    assert result.warmup.warmup_bars == expected_warmup
    assert result.validity.valid_from_index == expected_warmup

    for index in range(expected_warmup):
        assert np.isnan(signal[index])
        assert np.isnan(histogram[index])
    for index in range(expected_warmup, len(_CLOSES)):
        assert not np.isnan(signal[index])
        assert not np.isnan(line[index])
        assert not np.isnan(histogram[index])


def test_macd_component_is_causal_when_truncated_after_bar_n() -> None:
    fast_period, slow_period, signal_period = 3, 6, 3
    truncate_at = 14

    full = _run_macd(
        _CLOSES,
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-causal-full",
    )
    truncated = _run_macd(
        _CLOSES[: truncate_at + 1],
        fast_period=fast_period,
        slow_period=slow_period,
        signal_period=signal_period,
        source_id="macd-causal-truncated",
    )

    for output_id in ("line", "signal", "histogram"):
        full_values = np.asarray(full.outputs[OutputId(output_id)].values, dtype=np.float64)
        truncated_values = np.asarray(
            truncated.outputs[OutputId(output_id)].values, dtype=np.float64
        )
        for index in range(truncate_at + 1):
            if np.isnan(full_values[index]):
                assert np.isnan(truncated_values[index])
            else:
                assert truncated_values[index] == pytest.approx(full_values[index])
