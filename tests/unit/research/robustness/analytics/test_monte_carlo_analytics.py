"""Unit tests for Monte Carlo analytics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl

from trading_framework.research.robustness.analytics.monte_carlo import (
    build_monte_carlo_analytics,
    equity_path_from_pnls,
    run_monte_carlo_simulation,
)
from trading_framework.research.robustness.monte_carlo import (
    MonteCarloMethod,
    MonteCarloResults,
    MonteCarloSpec,
)
from trading_framework.research.simulation.facts import simulated_trade_schema


def _sample_trades() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "trade_id": ["t1", "t2", "t3", "t4"],
            "strategy_model_id": ["s", "s", "s", "s"],
            "instrument": ["ES.c.0", "ES.c.0", "ES.c.0", "ES.c.0"],
            "direction": ["long", "long", "short", "long"],
            "entry_signal_at": [datetime(2024, 1, 1, tzinfo=UTC)] * 4,
            "entry_fill_at": [datetime(2024, 1, 1, 14, 1, tzinfo=UTC)] * 4,
            "entry_fill_price": [100.0, 100.0, 100.0, 100.0],
            "exit_signal_at": [datetime(2024, 1, 1, 14, 5, tzinfo=UTC)] * 4,
            "exit_fill_at": [
                datetime(2024, 1, 1, 14, 6, tzinfo=UTC),
                datetime(2024, 1, 2, 14, 6, tzinfo=UTC),
                datetime(2024, 1, 3, 14, 6, tzinfo=UTC),
                datetime(2024, 1, 4, 14, 6, tzinfo=UTC),
            ],
            "exit_fill_price": [101.0, 99.0, 102.0, 101.0],
            "quantity": [1.0, 1.0, 1.0, 1.0],
            "gross_pnl": [10.0, -5.0, 20.0, 8.0],
            "commission_paid": [1.0, 1.0, 1.0, 1.0],
            "net_pnl": [9.0, -6.0, 19.0, 7.0],
            "bars_held": [3, 5, 7, 4],
            "exit_reason": ["fixed_bars", "fixed_bars", "fixed_bars", "fixed_bars"],
            "source_dataset_ref": ["dataset@1", "dataset@1", "dataset@1", "dataset@1"],
        },
        schema=simulated_trade_schema(),
    )


def test_run_monte_carlo_simulation_is_reproducible_with_seed() -> None:
    trades = _sample_trades()
    spec = MonteCarloSpec(
        methods=(MonteCarloMethod.TRADE_SHUFFLE,),
        path_count=20,
        rng_seed=123,
    )
    first = run_monte_carlo_simulation(
        trades=trades,
        spec=spec,
        initial_capital=Decimal("100000"),
    )
    second = run_monte_carlo_simulation(
        trades=trades,
        spec=spec,
        initial_capital=Decimal("100000"),
    )
    assert first[0].path_summaries == second[0].path_summaries


def test_run_monte_carlo_simulation_includes_all_methods() -> None:
    trades = _sample_trades()
    spec = MonteCarloSpec(path_count=10, rng_seed=1)
    method_results = run_monte_carlo_simulation(
        trades=trades,
        spec=spec,
        initial_capital=Decimal("100000"),
    )
    assert {result.method for result in method_results} == {
        MonteCarloMethod.TRADE_SHUFFLE.value,
        MonteCarloMethod.TRADE_BOOTSTRAP.value,
        MonteCarloMethod.BLOCK_BOOTSTRAP.value,
    }
    assert all(len(result.percentile_equity) == 4 for result in method_results)


def test_equity_path_from_pnls_tracks_drawdown() -> None:
    equity_points, terminal_equity, max_drawdown = equity_path_from_pnls(
        trade_pnls=[Decimal("10"), Decimal("-20"), Decimal("5")],
        initial_capital=Decimal("100"),
    )
    assert len(equity_points) == 3
    assert terminal_equity == Decimal("95")
    assert max_drawdown == Decimal("-20")


def test_build_monte_carlo_analytics_includes_tail_probabilities() -> None:
    trades = _sample_trades()
    spec = MonteCarloSpec(
        methods=(MonteCarloMethod.TRADE_BOOTSTRAP,),
        path_count=25,
        rng_seed=5,
        max_drawdown_threshold=Decimal("-100"),
    )
    method_results = run_monte_carlo_simulation(
        trades=trades,
        spec=spec,
        initial_capital=Decimal("100000"),
    )
    results = MonteCarloResults(
        experiment_id="exp-mc",
        reference_strategy_run_id="run-1",
        rng_seed=spec.rng_seed,
        methods=method_results,
    )
    analytics = build_monte_carlo_analytics(
        experiment_id="exp-mc",
        results=results,
        max_drawdown_threshold=spec.max_drawdown_threshold,
    )
    assert len(analytics.distribution_summaries) == 1
    assert analytics.tail_probabilities[0].probability_max_drawdown_exceeds_threshold is not None
