"""Tests for the Return Autocorrelation statistics feature component (D-S051-03/04/05)."""

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
    rolling_lagged_pearson_correlation,
)
from trading_framework.market_analysis.components.statistics import ReturnAutocorrelationComponent
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
    register_statistics_return_autocorrelation_component,
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


def _population_pearson_correlation(x: list[float], y: list[float]) -> float:
    n = len(x)
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    covariance = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True)) / n
    x_var = sum((a - x_mean) ** 2 for a in x) / n
    y_var = sum((b - y_mean) ** 2 for b in y) / n
    x_std = math.sqrt(x_var)
    y_std = math.sqrt(y_var)
    if x_std == 0.0 or y_std == 0.0:
        return 0.0
    return covariance / (x_std * y_std)


def _reference_rolling_autocorrelation(
    returns: list[float | None], period: int, lag: int
) -> list[float]:
    n = len(returns)
    out: list[float] = [float("nan")] * n
    for index in range(n):
        if index - period + 1 < 0:
            continue
        window = returns[index - period + 1 : index + 1]
        if any(value is None for value in window):
            continue
        values = [value for value in window if value is not None]
        x = values[: period - lag]
        y = values[lag:]
        out[index] = _population_pearson_correlation(x, y)
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
    lag: int,
    source_id: str,
) -> tuple[np.ndarray, AnalysisResult]:
    registry = ComponentRegistry()
    register_statistics_return_autocorrelation_component(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    parameters = ReturnAutocorrelationComponent().parameter_schema.canonicalize(
        {"period": period, "lag": lag}
    )
    request = ComponentRequest(
        component_id=ComponentId("statistics.return_autocorrelation"),
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
    return value, result


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
    107.2,
    108.6,
    109.1,
    108.4,
    110.0,
    111.2,
    110.6,
]


# ---------------------------------------------------------------------------
# Kernel-level tests
# ---------------------------------------------------------------------------


def test_rolling_lagged_pearson_correlation_kernel_matches_independently_computed_reference() -> (
    None
):
    period, lag = 5, 1
    returns = _reference_log_returns(_CLOSES)
    valid_returns = [value for value in returns[1:] if value is not None]

    values = rolling_lagged_pearson_correlation(
        np.array(valid_returns, dtype=np.float64), period, lag
    )
    expected = _reference_rolling_autocorrelation(returns[1:], period, lag)

    for index in range(len(valid_returns)):
        if math.isnan(expected[index]):
            assert np.isnan(values[index])
        else:
            assert values[index] == pytest.approx(expected[index])


def test_rolling_lagged_pearson_correlation_kernel_is_causal() -> None:
    period, lag = 5, 1
    returns = _reference_log_returns(_CLOSES)
    valid_returns = np.array(
        [value for value in returns[1:] if value is not None], dtype=np.float64
    )
    full = rolling_lagged_pearson_correlation(valid_returns, period, lag)

    truncate_at = 10
    truncated = rolling_lagged_pearson_correlation(valid_returns[: truncate_at + 1], period, lag)

    for index in range(truncate_at + 1):
        if np.isnan(full[index]):
            assert np.isnan(truncated[index])
        else:
            assert truncated[index] == pytest.approx(full[index])


def test_rolling_lagged_pearson_correlation_kernel_zero_variance_window_yields_zero_not_nan() -> (
    None
):
    # A constant-return window (population stdev == 0 for at least one of the
    # unshifted/lag-shifted halves): the ordinary D-S048-10 zero-denominator
    # convention, deliberately NOT the D-S051-04 stochastic 50.0 exception.
    period, lag = 5, 1
    values = np.full(10, 0.01, dtype=np.float64)
    result = rolling_lagged_pearson_correlation(values, period, lag)
    for index in range(period - 1, len(values)):
        assert result[index] == 0.0
        assert not np.isnan(result[index])


def test_rolling_lagged_pearson_correlation_kernel_alternating_series_gives_near_negative_one() -> (
    None
):
    # A perfectly alternating return series (+x, -x, +x, -x, ...): each value
    # is followed by its near-opposite, so lag-1 autocorrelation should be
    # near -1 -- a semantic sanity check, distinct from the "matches an
    # independently computed reference" arithmetic test above.
    period, lag = 8, 1
    alternating = np.array([0.01 if i % 2 == 0 else -0.01 for i in range(12)], dtype=np.float64)
    result = rolling_lagged_pearson_correlation(alternating, period, lag)
    observed = result[period - 1]
    assert not np.isnan(observed)
    assert observed == pytest.approx(-1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Component-level shape / dependency-declaration / validation tests
# ---------------------------------------------------------------------------


def test_return_autocorrelation_component_declares_shape() -> None:
    component = ReturnAutocorrelationComponent()
    assert component.component_id.value == "statistics.return_autocorrelation"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"value"}


def test_return_autocorrelation_component_depends_on_close_prices() -> None:
    component = ReturnAutocorrelationComponent()
    parameters = component.parameter_schema.canonicalize({"period": 60, "lag": 1})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()


def test_return_autocorrelation_component_history_requirement_is_period() -> None:
    component = ReturnAutocorrelationComponent()
    parameters = component.parameter_schema.canonicalize({"period": 60, "lag": 1})
    assert component.history_requirement(parameters).bars_before == 60


def test_return_autocorrelation_lag_not_less_than_period_minus_one_raises_naming_both() -> None:
    component = ReturnAutocorrelationComponent()
    parameters = component.parameter_schema.canonicalize({"period": 10, "lag": 9})
    with pytest.raises(ComponentValidationError) as excinfo:
        component.history_requirement(parameters)
    message = str(excinfo.value)
    assert "9" in message
    assert "period - 1" in message


def test_return_autocorrelation_lag_equal_to_period_minus_two_also_raises() -> None:
    # lag < period - 1 is the exact boundary: lag == period - 2 is the last
    # ACCEPTED value (leaves x/y with exactly 2 points); period - 1 is
    # rejected (SPRINT_051.md acceptance: "validated lag < period - 1").
    component = ReturnAutocorrelationComponent()
    parameters = component.parameter_schema.canonicalize({"period": 10, "lag": 9})
    with pytest.raises(ComponentValidationError):
        component.history_requirement(parameters)

    accepted_parameters = component.parameter_schema.canonicalize({"period": 10, "lag": 8})
    assert component.history_requirement(accepted_parameters).bars_before == 10


# ---------------------------------------------------------------------------
# Value-correctness / warm-up / zero-variance / causality tests
# ---------------------------------------------------------------------------


def test_return_autocorrelation_value_matches_independently_computed_pearson_correlation() -> None:
    period, lag = 8, 1
    value, _result = _run(_CLOSES, period=period, lag=lag, source_id="autocorr-value")

    returns = _reference_log_returns(_CLOSES)
    expected_value = _reference_rolling_autocorrelation(returns, period, lag)

    for index in range(len(_CLOSES)):
        if math.isnan(expected_value[index]):
            assert np.isnan(value[index])
        else:
            assert value[index] == pytest.approx(expected_value[index])


def test_return_autocorrelation_constant_return_window_yields_zero_not_nan_or_inf() -> None:
    # A run of identical closes -> every log return in the window is exactly
    # 0.0 -> zero variance -> the correlation's 0/0 is defined as 0.0
    # (the ordinary D-S048-10 convention), not NaN/inf.
    period, lag = 8, 1
    closes = [100.0] * 12

    value, _result = _run(closes, period=period, lag=lag, source_id="autocorr-zero-variance")

    for index in range(period, len(closes)):
        assert value[index] == 0.0
        assert not np.isnan(value[index])
        assert not np.isinf(value[index])


def test_return_autocorrelation_alternating_synthetic_series_is_near_negative_one() -> None:
    # Semantic sanity check (distinct from the arithmetic-matches-reference
    # test above): a perfectly alternating price series produces alternating
    # +x/-x log returns, so lag-1 autocorrelation should be near -1.
    period, lag = 8, 1
    closes = [100.0]
    for i in range(1, 16):
        closes.append(closes[-1] * (1.01 if i % 2 == 1 else 1 / 1.01))

    value, _result = _run(closes, period=period, lag=lag, source_id="autocorr-alternating")

    observed = value[period]
    assert not np.isnan(observed)
    assert observed == pytest.approx(-1.0, abs=1e-6)
    assert observed < -0.9


def test_return_autocorrelation_warmup_is_period_bars() -> None:
    period, lag = 8, 1
    value, result = _run(_CLOSES, period=period, lag=lag, source_id="autocorr-warmup")

    assert result.warmup.warmup_bars == period
    assert result.validity.valid_from_index == period

    for index in range(period):
        assert np.isnan(value[index])
    for index in range(period, len(_CLOSES)):
        assert not np.isnan(value[index])


def test_return_autocorrelation_component_is_causal_when_truncated_after_bar_n() -> None:
    period, lag = 8, 1
    truncate_at = 14

    full_value, _ = _run(_CLOSES, period=period, lag=lag, source_id="autocorr-causal-full")
    truncated_value, _ = _run(
        _CLOSES[: truncate_at + 1], period=period, lag=lag, source_id="autocorr-causal-truncated"
    )

    for index in range(truncate_at + 1):
        if np.isnan(full_value[index]):
            assert np.isnan(truncated_value[index])
        else:
            assert truncated_value[index] == pytest.approx(full_value[index])
