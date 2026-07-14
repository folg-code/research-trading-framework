"""Unit tests for Strategy Research dashboard view model types."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import polars as pl

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.research.analytics.strategy_dashboard import (
    StrategyDashboardMetadata,
    StrategyDashboardMetricContext,
    StrategyDashboardOverviewKpis,
    StrategyDashboardPerformancePanels,
    StrategyDashboardViewModel,
    effective_equity_range,
    equity_dataframe_to_rows,
    market_bars_to_rows,
    strategy_dashboard_view_model_to_dict,
    trades_dataframe_to_rows,
)
from trading_framework.research.simulation.facts import (
    equity_point_schema,
    simulated_trade_schema,
)


def _market_bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("95")),
        close=Price(Decimal("102")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_market_bars_to_rows_preserves_values() -> None:
    rows = market_bars_to_rows([_market_bar(0), _market_bar(1)])

    assert len(rows) == 2
    assert rows[0].open == 100.0
    assert rows[0].high == 105.0
    assert rows[1].close == 102.0


def test_effective_equity_range_returns_bounds() -> None:
    equity = pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, 3, tzinfo=UTC),
                datetime(2024, 1, 1, 2, tzinfo=UTC),
            ],
            "equity": [1000.0, 1010.0, 1005.0],
            "drawdown": [0.0, -1.0, -0.5],
            "open_position_count": [0, 0, 0],
        },
        schema=equity_point_schema(),
    )

    start, end = effective_equity_range(equity)

    assert start == datetime(2024, 1, 1, 1, tzinfo=UTC)
    assert end == datetime(2024, 1, 1, 3, tzinfo=UTC)


def test_strategy_dashboard_view_model_to_dict_is_json_serializable() -> None:
    observed_at = datetime(2024, 1, 1, tzinfo=UTC)
    view_model = StrategyDashboardViewModel(
        run_id="run-1",
        source_dataset_ref="ES.c.0|ohlcv|1m|csv|fixture@1",
        strategy_model_id="strategy_a",
        market_model_id="market_a",
        signal_model_id="signal_a",
        exit_model_id="fixed_bars",
        risk_model_id="fixed_quantity",
        simulation_assumptions_fingerprint="abc123",
        overview=StrategyDashboardOverviewKpis(
            net_pnl=Decimal("9"),
            total_return=0.00009,
            max_drawdown=Decimal("0"),
            current_drawdown=Decimal("0"),
            sharpe_ratio=None,
            sortino_ratio=None,
            profit_factor=None,
            expectancy=Decimal("9"),
            trade_count=1,
            win_rate=1.0,
            avg_win=Decimal("9"),
            avg_loss=None,
            total_costs=Decimal("1"),
        ),
        performance=StrategyDashboardPerformancePanels(
            monthly_pnl=(),
            trade_pnl_histogram=(),
            direction_breakdown=(),
            session_breakdown=(),
            hour_breakdown=(),
            recent_trades=trades_dataframe_to_rows(
                pl.DataFrame(
                    {
                        "trade_id": ["t1"],
                        "strategy_model_id": ["strategy_a"],
                        "instrument": ["ES.c.0"],
                        "direction": ["long"],
                        "entry_signal_at": [observed_at],
                        "entry_fill_at": [observed_at],
                        "entry_fill_price": [100.0],
                        "exit_signal_at": [observed_at],
                        "exit_fill_at": [observed_at],
                        "exit_fill_price": [101.0],
                        "quantity": [1.0],
                        "gross_pnl": [10.0],
                        "commission_paid": [1.0],
                        "net_pnl": [9.0],
                        "bars_held": [3],
                        "exit_reason": ["fixed_bars"],
                        "source_dataset_ref": ["dataset@1"],
                    },
                    schema=simulated_trade_schema(),
                )
            ),
        ),
        metric_context=StrategyDashboardMetricContext(
            warnings=(),
            sharpe_annualization="daily_equity_returns_sqrt_252",
            sample_eligible=False,
            min_recommended_trades=30,
        ),
        trades=trades_dataframe_to_rows(
            pl.DataFrame(
                {
                    "trade_id": ["t1"],
                    "strategy_model_id": ["strategy_a"],
                    "instrument": ["ES.c.0"],
                    "direction": ["long"],
                    "entry_signal_at": [observed_at],
                    "entry_fill_at": [observed_at],
                    "entry_fill_price": [100.0],
                    "exit_signal_at": [observed_at],
                    "exit_fill_at": [observed_at],
                    "exit_fill_price": [101.0],
                    "quantity": [1.0],
                    "gross_pnl": [10.0],
                    "commission_paid": [1.0],
                    "net_pnl": [9.0],
                    "bars_held": [3],
                    "exit_reason": ["fixed_bars"],
                    "source_dataset_ref": ["dataset@1"],
                },
                schema=simulated_trade_schema(),
            )
        ),
        equity=equity_dataframe_to_rows(
            pl.DataFrame(
                {
                    "observed_at": [observed_at],
                    "equity": [1009.0],
                    "drawdown": [0.0],
                    "open_position_count": [0],
                },
                schema=equity_point_schema(),
            )
        ),
        bars=market_bars_to_rows([_market_bar(0)]),
        metadata=StrategyDashboardMetadata(
            evaluation_timeframe="1m",
            bar_count=1,
            effective_from_utc=observed_at,
            effective_to_utc=observed_at,
        ),
    )

    payload = strategy_dashboard_view_model_to_dict(view_model)
    serialized = json.dumps(payload)

    assert '"run_id": "run-1"' in serialized
    assert payload["sections"]["overview"]["trade_count"] == 1
    assert payload["sections"]["conditional"]["market_model_id"] == "market_a"
    assert payload["bars"][0]["close"] == 102.0
