"""Tests for the Relative Volatility feature component (D-S051-03/05)."""

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
    ComponentRequest,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.adapters.numpy.kernels import (
    log_returns,
    rolling_population_stdev,
)
from trading_framework.market_analysis.components.volatility import RelativeVolatilityComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.errors import ComponentValidationError
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import (
    register_relative_volatility_component,
)
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe

# ---------------------------------------------------------------------------
# Independent, from-first-principles reference (never calls the kernel)
# ---------------------------------------------------------------------------


def _reference_log_returns(closes: list[float]) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    for index in range(1, len(closes)):
        out[index] = math.log(closes[index] / closes[index - 1])
    return out


def _population_stdev(values: list[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _reference_rolling_stdev(returns: list[float | None], period: int) -> list[float]:
    n = len(returns)
    out: list[float] = [float("nan")] * n
    for index in range(n):
        if index - period + 1 < 0:
            continue
        window = returns[index - period + 1 : index + 1]
        if any(value is None for value in window):
            continue
        out[index] = _population_stdev([value for value in window if value is not None])
    return out


def _reference_ratio(value: list[float], baseline: list[float]) -> list[float]:
    out: list[float] = [float("nan")] * len(value)
    for index in range(len(value)):
        b = baseline[index]
        v = value[index]
        if math.isnan(b):
            continue
        if b == 0.0:
            out[index] = 0.0
        elif math.isnan(v):
            continue
        else:
            out[index] = v / b
    return out


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


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


def _run(
    closes: list[float],
    *,
    period: int,
    baseline_period: int,
    source_id: str,
) -> tuple[np.ndarray, np.ndarray, AnalysisResult]:
    registry = ComponentRegistry()
    register_relative_volatility_component(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    parameters = RelativeVolatilityComponent().parameter_schema.canonicalize(
        {"period": period, "baseline_period": baseline_period}
    )
    request = ComponentRequest(
        component_id=ComponentId("volatility.relative_volatility"),
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
    result = next(iter(workspace.result_store.results().values()))
    value = np.asarray(result.outputs[OutputId("value")].values, dtype=np.float64)
    ratio = np.asarray(result.outputs[OutputId("ratio")].values, dtype=np.float64)
    return value, ratio, result


_CLOSES = [
    100.0,
    101.0,
    100.5,
    102.0,
    101.5,
    103.0,
    104.0,
    103.5,
    105.0,
    106.0,
    105.5,
    107.0,
    108.0,
]


# ---------------------------------------------------------------------------
# Kernel-level tests
# ---------------------------------------------------------------------------


def test_log_returns_kernel_matches_independently_computed_reference() -> None:
    values = log_returns(np.array(_CLOSES, dtype=np.float64))
    expected = _reference_log_returns(_CLOSES)

    assert np.isnan(values[0])
    for index in range(1, len(_CLOSES)):
        assert values[index] == pytest.approx(expected[index])


def test_log_returns_kernel_loses_one_bar() -> None:
    values = log_returns(np.array(_CLOSES, dtype=np.float64))
    assert np.isnan(values[0])
    assert not np.isnan(values[1])


def test_rolling_population_stdev_kernel_matches_independently_computed_reference() -> None:
    period = 3
    returns = _reference_log_returns(_CLOSES)
    valid_returns = [value for value in returns[1:] if value is not None]

    values = rolling_population_stdev(np.array(valid_returns, dtype=np.float64), period)
    expected = _reference_rolling_stdev(returns[1:], period)

    for index in range(len(valid_returns)):
        if math.isnan(expected[index]):
            assert np.isnan(values[index])
        else:
            assert values[index] == pytest.approx(expected[index])


def test_rolling_population_stdev_kernel_uses_ddof_zero() -> None:
    # A hand-computed two-value population stdev: mean=1.5, both points at
    # distance 0.5 -> population variance = 0.25 -> population stdev = 0.5.
    # (Sample stdev, ddof=1, would give ~0.7071 instead -- this asserts the
    # POPULATION estimator explicitly, per D-S051-05.)
    values = np.array([1.0, 2.0], dtype=np.float64)
    result = rolling_population_stdev(values, 2)
    assert result[1] == pytest.approx(0.5)


def test_rolling_population_stdev_kernel_is_causal() -> None:
    period = 3
    returns = _reference_log_returns(_CLOSES)
    valid_returns = np.array(
        [value for value in returns[1:] if value is not None], dtype=np.float64
    )
    full = rolling_population_stdev(valid_returns, period)

    truncate_at = 6
    truncated = rolling_population_stdev(valid_returns[: truncate_at + 1], period)

    for index in range(truncate_at + 1):
        if np.isnan(full[index]):
            assert np.isnan(truncated[index])
        else:
            assert truncated[index] == pytest.approx(full[index])


# ---------------------------------------------------------------------------
# Component-level shape / dependency-declaration tests
# ---------------------------------------------------------------------------


def test_relative_volatility_component_declares_shape() -> None:
    component = RelativeVolatilityComponent()
    assert component.component_id.value == "volatility.relative_volatility"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value", "ratio"}


def test_relative_volatility_component_depends_on_close_prices() -> None:
    component = RelativeVolatilityComponent()
    parameters = component.parameter_schema.canonicalize({"period": 20, "baseline_period": 100})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()


def test_relative_volatility_component_history_requirement_is_baseline_period() -> None:
    component = RelativeVolatilityComponent()
    parameters = component.parameter_schema.canonicalize({"period": 20, "baseline_period": 100})
    assert component.history_requirement(parameters).bars_before == 100


def test_relative_volatility_period_greater_or_equal_baseline_raises_naming_both() -> None:
    component = RelativeVolatilityComponent()
    parameters = component.parameter_schema.canonicalize({"period": 20, "baseline_period": 20})
    with pytest.raises(ComponentValidationError) as excinfo:
        component.history_requirement(parameters)
    message = str(excinfo.value)
    assert "20" in message


def test_relative_volatility_period_strictly_greater_than_baseline_also_raises() -> None:
    component = RelativeVolatilityComponent()
    parameters = component.parameter_schema.canonicalize({"period": 150, "baseline_period": 100})
    with pytest.raises(ComponentValidationError) as excinfo:
        component.history_requirement(parameters)
    message = str(excinfo.value)
    assert "150" in message
    assert "100" in message


# ---------------------------------------------------------------------------
# Value-correctness / warm-up / zero-baseline / causality tests
# ---------------------------------------------------------------------------


def test_relative_volatility_value_matches_independently_computed_population_stdev() -> None:
    period, baseline_period = 3, 6
    value, _ratio, _result = _run(
        _CLOSES,
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-value",
    )

    returns = _reference_log_returns(_CLOSES)
    expected_value = _reference_rolling_stdev(returns, period)

    for index in range(len(_CLOSES)):
        if math.isnan(expected_value[index]):
            assert np.isnan(value[index])
        else:
            assert value[index] == pytest.approx(expected_value[index])


def test_relative_volatility_ratio_uses_baseline_period_estimator() -> None:
    period, baseline_period = 3, 6
    _value, ratio, _result = _run(
        _CLOSES,
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-ratio",
    )

    returns = _reference_log_returns(_CLOSES)
    expected_value = _reference_rolling_stdev(returns, period)
    expected_baseline = _reference_rolling_stdev(returns, baseline_period)
    expected_ratio = _reference_ratio(expected_value, expected_baseline)

    for index in range(len(_CLOSES)):
        if math.isnan(expected_ratio[index]):
            assert np.isnan(ratio[index])
        else:
            assert ratio[index] == pytest.approx(expected_ratio[index])


def test_relative_volatility_zero_baseline_yields_zero_not_nan_or_inf() -> None:
    # A perfectly flat baseline window (every log return in it exactly 0.0)
    # -- the project's ORDINARY zero-denominator convention (D-S048-10),
    # deliberately NOT the D-S051-04 50.0-midpoint exception (that is
    # momentum.stochastic-specific and does not generalize to a volatility
    # ratio).
    period, baseline_period = 2, 4
    closes = [100.0] * 10

    value, ratio, _result = _run(
        closes,
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-zero-baseline",
    )

    warmup = baseline_period
    for index in range(warmup, len(closes)):
        assert value[index] == pytest.approx(0.0)
        assert ratio[index] == 0.0
        assert not np.isinf(ratio[index])
        assert not np.isnan(ratio[index])


def test_relative_volatility_warmup_is_baseline_period() -> None:
    period, baseline_period = 3, 6
    value, ratio, result = _run(
        _CLOSES,
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-warmup",
    )

    assert result.warmup.warmup_bars == baseline_period
    assert result.validity.valid_from_index == baseline_period

    for index in range(baseline_period, len(_CLOSES)):
        assert not np.isnan(value[index])
        assert not np.isnan(ratio[index])


def test_relative_volatility_component_is_causal_when_truncated_after_bar_n() -> None:
    period, baseline_period = 3, 6
    truncate_at = 10

    full_value, full_ratio, _ = _run(
        _CLOSES,
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-causal-full",
    )
    truncated_value, truncated_ratio, _ = _run(
        _CLOSES[: truncate_at + 1],
        period=period,
        baseline_period=baseline_period,
        source_id="relvol-causal-truncated",
    )

    for full, truncated in ((full_value, truncated_value), (full_ratio, truncated_ratio)):
        for index in range(truncate_at + 1):
            if np.isnan(full[index]):
                assert np.isnan(truncated[index])
            else:
                assert truncated[index] == pytest.approx(full[index])
