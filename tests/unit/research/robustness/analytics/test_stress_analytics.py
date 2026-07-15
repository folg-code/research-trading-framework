"""Unit tests for stress analytics post-processors and comparison table."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl

from trading_framework.research.analytics.strategy_summarize import StrategyRunSummary
from trading_framework.research.robustness.analytics.stress import (
    apply_remove_top_days_stress,
    apply_remove_top_trades_stress,
    build_stress_comparison_table,
)
from trading_framework.research.robustness.stress import (
    StressScenarioResult,
    StressScenarioSpec,
)
from trading_framework.research.simulation.facts import equity_point_schema, simulated_trade_schema


def _sample_trades() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "trade_id": ["t1", "t2", "t3"],
            "strategy_model_id": ["s", "s", "s"],
            "instrument": ["ES.c.0", "ES.c.0", "ES.c.0"],
            "direction": ["long", "long", "short"],
            "entry_signal_at": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                datetime(2024, 1, 3, tzinfo=UTC),
            ],
            "entry_fill_at": [
                datetime(2024, 1, 1, 14, 1, tzinfo=UTC),
                datetime(2024, 1, 2, 14, 1, tzinfo=UTC),
                datetime(2024, 1, 3, 14, 1, tzinfo=UTC),
            ],
            "entry_fill_price": [100.0, 100.0, 100.0],
            "exit_signal_at": [
                datetime(2024, 1, 1, 14, 5, tzinfo=UTC),
                datetime(2024, 1, 2, 14, 5, tzinfo=UTC),
                datetime(2024, 1, 3, 14, 5, tzinfo=UTC),
            ],
            "exit_fill_at": [
                datetime(2024, 1, 1, 14, 6, tzinfo=UTC),
                datetime(2024, 1, 2, 14, 6, tzinfo=UTC),
                datetime(2024, 1, 3, 14, 6, tzinfo=UTC),
            ],
            "exit_fill_price": [101.0, 99.0, 102.0],
            "quantity": [1.0, 1.0, 1.0],
            "gross_pnl": [10.0, -5.0, 20.0],
            "commission_paid": [1.0, 1.0, 1.0],
            "net_pnl": [9.0, -6.0, 19.0],
            "bars_held": [3, 5, 7],
            "exit_reason": ["fixed_bars", "fixed_bars", "fixed_bars"],
            "source_dataset_ref": ["dataset@1", "dataset@1", "dataset@1"],
        },
        schema=simulated_trade_schema(),
    )


def _sample_equity() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
                datetime(2024, 1, 3, tzinfo=UTC),
            ],
            "equity": [100000.0, 100009.0, 100022.0],
            "drawdown": [0.0, 0.0, -6.0],
            "open_position_count": [0, 0, 0],
        },
        schema=equity_point_schema(),
    )


def test_apply_remove_top_trades_stress_drops_best_trade() -> None:
    trades = _sample_trades()
    equity = _sample_equity()
    scenario = StressScenarioSpec(scenario_id="remove_top", remove_top_n_trades=1)
    filtered_trades, _, summary = apply_remove_top_trades_stress(
        trades=trades,
        equity=equity,
        scenario=scenario,
        initial_capital=Decimal("100000"),
    )
    assert len(filtered_trades) == 2
    assert "t3" not in filtered_trades.get_column("trade_id").to_list()
    assert summary.net_pnl == Decimal("3")


def test_apply_remove_top_days_stress_drops_best_day() -> None:
    trades = _sample_trades()
    equity = _sample_equity()
    scenario = StressScenarioSpec(scenario_id="remove_day", remove_top_n_days=1)
    filtered_trades, _, summary = apply_remove_top_days_stress(
        trades=trades,
        equity=equity,
        scenario=scenario,
        initial_capital=Decimal("100000"),
    )
    assert len(filtered_trades) == 2
    assert summary.net_pnl == Decimal("3")


def test_build_stress_comparison_table_includes_delta() -> None:
    baseline = StrategyRunSummary(
        trade_count=3,
        win_count=2,
        loss_count=1,
        win_rate=2 / 3,
        gross_pnl=Decimal("25"),
        net_pnl=Decimal("22"),
        total_commission=Decimal("3"),
        max_drawdown=Decimal("-6"),
        final_equity=Decimal("100022"),
    )
    analytics = build_stress_comparison_table(
        experiment_id="exp-stress",
        baseline_summary=baseline,
        baseline_strategy_run_id="baseline-run",
        scenario_results=(
            StressScenarioResult(
                scenario_id="double_commission",
                scenario_fingerprint="abc",
                mode="RERUN",
                status="COMPLETED",
                strategy_run_id="run-1",
                net_pnl="18",
                trade_count=3,
            ),
        ),
    )
    assert analytics.baseline_net_pnl == Decimal("22")
    assert len(analytics.rows) == 1
    assert analytics.rows[0].delta_net_pnl == Decimal("-4")
