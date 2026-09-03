"""Tests for the Return Distribution statistics feature component (D-S051-03/04/05)."""

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
from trading_framework.market_analysis.adapters.numpy.kernels import rolling_skew_and_kurtosis
from trading_framework.market_analysis.components.statistics import ReturnDistributionComponent
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
    register_statistics_return_distribution_component,
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


def _population_skew_and_kurtosis(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    m2 = sum((value - mean) ** 2 for value in values) / n
    m3 = sum((value - mean) ** 3 for value in values) / n
    m4 = sum((value - mean) ** 4 for value in values) / n
    if m2 == 0.0:
        return 0.0, 0.0
    skew = m3 / m2**1.5
    excess_kurtosis = m4 / m2**2 - 3.0
    return skew, excess_kurtosis


def _reference_rolling_distribution(
    returns: list[float | None], period: int
) -> tuple[list[float], list[float]]:
    n = len(returns)
    skew_out: list[float] = [float("nan")] * n
    kurtosis_out: list[float] = [float("nan")] * n
    for index in range(n):
        if index - period + 1 < 0:
            continue
        window = returns[index - period + 1 : index + 1]
        if any(value is None for value in window):
            continue
        values = [value for value in window if value is not None]
        skew_out[index], kurtosis_out[index] = _population_skew_and_kurtosis(values)
    return skew_out, kurtosis_out


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
    source_id: str,
) -> tuple[np.ndarray, np.ndarray, AnalysisResult]:
    registry = ComponentRegistry()
    register_statistics_return_distribution_component(registry)
    view = AnalysisDataView.from_bars(_bars(closes))
    planner = DependencyPlanner(registry)
    parameters = ReturnDistributionComponent().parameter_schema.canonicalize({"period": period})
    request = ComponentRequest(
        component_id=ComponentId("statistics.return_distribution"),
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
    skew = np.asarray(result.outputs[OutputId("skew")].values, dtype=np.float64)
    excess_kurtosis = np.asarray(
        result.outputs[OutputId("excess_kurtosis")].values, dtype=np.float64
    )
    return skew, excess_kurtosis, result


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


def test_rolling_skew_and_kurtosis_kernel_matches_independently_computed_reference() -> None:
    period = 5
    returns = _reference_log_returns(_CLOSES)
    valid_returns = [value for value in returns[1:] if value is not None]

    skew, kurtosis = rolling_skew_and_kurtosis(np.array(valid_returns, dtype=np.float64), period)
    expected_skew, expected_kurtosis = _reference_rolling_distribution(returns[1:], period)

    for index in range(len(valid_returns)):
        if math.isnan(expected_skew[index]):
            assert np.isnan(skew[index])
            assert np.isnan(kurtosis[index])
        else:
            assert skew[index] == pytest.approx(expected_skew[index])
            assert kurtosis[index] == pytest.approx(expected_kurtosis[index])


def test_rolling_skew_and_kurtosis_kernel_is_causal() -> None:
    period = 5
    returns = _reference_log_returns(_CLOSES)
    valid_returns = np.array(
        [value for value in returns[1:] if value is not None], dtype=np.float64
    )
    full_skew, full_kurtosis = rolling_skew_and_kurtosis(valid_returns, period)

    truncate_at = 10
    truncated_skew, truncated_kurtosis = rolling_skew_and_kurtosis(
        valid_returns[: truncate_at + 1], period
    )

    for index in range(truncate_at + 1):
        if np.isnan(full_skew[index]):
            assert np.isnan(truncated_skew[index])
            assert np.isnan(truncated_kurtosis[index])
        else:
            assert truncated_skew[index] == pytest.approx(full_skew[index])
            assert truncated_kurtosis[index] == pytest.approx(full_kurtosis[index])


def test_rolling_skew_and_kurtosis_kernel_zero_variance_window_yields_zero_not_nan() -> None:
    # A constant-return window (population variance == 0): the ordinary
    # D-S048-10 zero-denominator convention, deliberately NOT the D-S051-04
    # stochastic 50.0 exception.
    period = 5
    values = np.full(10, 0.01, dtype=np.float64)
    skew, kurtosis = rolling_skew_and_kurtosis(values, period)
    for index in range(period - 1, len(values)):
        assert skew[index] == 0.0
        assert kurtosis[index] == 0.0
        assert not np.isnan(skew[index])
        assert not np.isnan(kurtosis[index])


def test_rolling_skew_and_kurtosis_kernel_normal_ish_sample_gives_near_zero_excess_kurtosis() -> (
    None
):
    # Semantic sanity check: a seeded normal sample's population excess
    # kurtosis approaches 0 in the population limit. A finite sample (n=500)
    # will be close but not exact; abs=0.5 is a generous tolerance chosen
    # because higher moments converge slowly (the 4th moment's sampling
    # variance is large even at a few hundred draws) -- the point is "not
    # wildly non-normal", not exact convergence.
    rng = np.random.default_rng(seed=51)
    period = 500
    sample = rng.normal(loc=0.0, scale=0.01, size=period)

    _skew, kurtosis = rolling_skew_and_kurtosis(sample, period)
    observed = kurtosis[period - 1]

    assert not np.isnan(observed)
    assert observed == pytest.approx(0.0, abs=0.5)


# ---------------------------------------------------------------------------
# Component-level shape / dependency-declaration tests
# ---------------------------------------------------------------------------


def test_return_distribution_component_declares_shape() -> None:
    component = ReturnDistributionComponent()
    assert component.component_id.value == "statistics.return_distribution"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"skew", "excess_kurtosis"}


def test_return_distribution_component_depends_on_close_prices() -> None:
    component = ReturnDistributionComponent()
    parameters = component.parameter_schema.canonicalize({"period": 60})
    fields = {dependency.field for dependency in component.data_dependencies(parameters)}
    assert fields == {"close"}
    assert component.component_dependencies(parameters) == ()


def test_return_distribution_component_history_requirement_is_period() -> None:
    component = ReturnDistributionComponent()
    parameters = component.parameter_schema.canonicalize({"period": 60})
    assert component.history_requirement(parameters).bars_before == 60


# ---------------------------------------------------------------------------
# Value-correctness / warm-up / zero-variance / sanity-check / causality tests
# ---------------------------------------------------------------------------


def test_return_distribution_values_match_independently_computed_moments() -> None:
    period = 8
    skew, kurtosis, _result = _run(_CLOSES, period=period, source_id="distribution-value")

    returns = _reference_log_returns(_CLOSES)
    expected_skew, expected_kurtosis = _reference_rolling_distribution(returns, period)

    for index in range(len(_CLOSES)):
        if math.isnan(expected_skew[index]):
            assert np.isnan(skew[index])
            assert np.isnan(kurtosis[index])
        else:
            assert skew[index] == pytest.approx(expected_skew[index])
            assert kurtosis[index] == pytest.approx(expected_kurtosis[index])


def test_return_distribution_constant_close_window_yields_zero_not_nan_or_inf() -> None:
    # A run of identical closes -> every log return in the window is exactly
    # 0.0 -> zero variance -> skew/excess_kurtosis's 0/0 is defined as 0.0
    # (the ordinary D-S048-10 convention), not NaN/inf.
    period = 8
    closes = [100.0] * 12

    skew, kurtosis, _result = _run(closes, period=period, source_id="distribution-zero-variance")

    for index in range(period, len(closes)):
        assert skew[index] == 0.0
        assert kurtosis[index] == 0.0
        assert not np.isnan(skew[index])
        assert not np.isinf(skew[index])
        assert not np.isnan(kurtosis[index])
        assert not np.isinf(kurtosis[index])


def test_return_distribution_normal_ish_synthetic_series_has_near_zero_excess_kurtosis() -> None:
    # Semantic sanity check (distinct from the arithmetic-matches-reference
    # test above): a seeded normal-ish log-return series should produce
    # excess kurtosis near 0, since a normal distribution's population
    # excess kurtosis is exactly 0. abs=0.5 tolerance, same justification as
    # the kernel-level sanity check above.
    period = 200
    rng = np.random.default_rng(seed=52)
    closes = [10000.0]
    for return_value in rng.normal(loc=0.0, scale=0.001, size=period + 50):
        closes.append(closes[-1] * math.exp(return_value))

    _skew, kurtosis, _result = _run(closes, period=period, source_id="distribution-normal-sanity")

    observed = kurtosis[-1]
    assert not np.isnan(observed)
    assert observed == pytest.approx(0.0, abs=0.5)


def test_return_distribution_warmup_is_period_bars() -> None:
    period = 8
    skew, kurtosis, result = _run(_CLOSES, period=period, source_id="distribution-warmup")

    assert result.warmup.warmup_bars == period
    assert result.validity.valid_from_index == period

    for index in range(period):
        assert np.isnan(skew[index])
        assert np.isnan(kurtosis[index])
    for index in range(period, len(_CLOSES)):
        assert not np.isnan(skew[index])
        assert not np.isnan(kurtosis[index])


def test_return_distribution_component_is_causal_when_truncated_after_bar_n() -> None:
    period = 8
    truncate_at = 14

    full_skew, full_kurtosis, _ = _run(_CLOSES, period=period, source_id="distribution-causal-full")
    truncated_skew, truncated_kurtosis, _ = _run(
        _CLOSES[: truncate_at + 1], period=period, source_id="distribution-causal-truncated"
    )

    for index in range(truncate_at + 1):
        if np.isnan(full_skew[index]):
            assert np.isnan(truncated_skew[index])
            assert np.isnan(truncated_kurtosis[index])
        else:
            assert truncated_skew[index] == pytest.approx(full_skew[index])
            assert truncated_kurtosis[index] == pytest.approx(full_kurtosis[index])
