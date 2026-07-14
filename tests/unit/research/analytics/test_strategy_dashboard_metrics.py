"""Unit tests for Strategy Research dashboard metrics computation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import polars as pl

from trading_framework.research.analytics.strategy_dashboard_metrics import (
    compute_strategy_dashboard_analytics,
)
from trading_framework.research.simulation.facts import (
    empty_simulated_trades_dataframe,
    equity_point_schema,
    simulated_trade_schema,
)


def test_compute_dashboard_analytics_zero_trades() -> None:
    equity = pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 2, tzinfo=UTC),
            ],
            "equity": [100000.0, 100000.0],
            "drawdown": [0.0, 0.0],
            "open_position_count": [0, 0],
        },
        schema=equity_point_schema(),
    )

    analytics = compute_strategy_dashboard_analytics(
        trades=empty_simulated_trades_dataframe(),
        equity=equity,
        evaluation_timeframe="1m",
        recent_trade_rows=(),
    )

    assert analytics.overview.trade_count == 0
    assert analytics.overview.total_return == 0.0
    assert analytics.overview.profit_factor is None
    assert analytics.overview.expectancy is None
    assert analytics.performance.monthly_pnl == ()
    assert any(warning.code == "NO_TRADES" for warning in analytics.metric_context.warnings)


def test_compute_dashboard_analytics_extended_metrics() -> None:
    trades = pl.DataFrame(
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
    equity = pl.DataFrame(
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

    analytics = compute_strategy_dashboard_analytics(
        trades=trades,
        equity=equity,
        evaluation_timeframe="1m",
        recent_trade_rows=(),
    )

    assert analytics.overview.trade_count == 3
    assert analytics.overview.profit_factor == (10.0 + 20.0) / 5.0
    assert analytics.overview.expectancy == Decimal(str(22.0 / 3))
    assert analytics.overview.avg_win == Decimal("14")
    assert analytics.overview.avg_loss == Decimal("-6")
    assert analytics.overview.total_costs == Decimal("3")
    assert len(analytics.performance.direction_breakdown) == 2
    assert len(analytics.performance.monthly_pnl) == 1
    assert analytics.metric_context.sample_eligible is False
