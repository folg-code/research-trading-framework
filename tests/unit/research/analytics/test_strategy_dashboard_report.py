"""Tests for Strategy Research dashboard HTML reports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from trading_framework.research.analytics.strategy_dashboard import (
    DirectionBreakdownRow,
    EquityPointRow,
    HourBreakdownRow,
    MonthlyPnlRow,
    OhlcvBarRow,
    SessionBreakdownRow,
    StrategyDashboardMetadata,
    StrategyDashboardMetricContext,
    StrategyDashboardMetricWarning,
    StrategyDashboardOverviewKpis,
    StrategyDashboardPerformancePanels,
    StrategyDashboardViewModel,
    TradeMarkerRow,
    TradePnlBucket,
)
from trading_framework.research.analytics.strategy_dashboard_report import (
    render_strategy_research_dashboard,
)


def _sample_view_model() -> StrategyDashboardViewModel:
    observed_at = datetime(2024, 1, 1, 14, 0, tzinfo=UTC)
    bar_time = observed_at + timedelta(minutes=1)
    trade = TradeMarkerRow(
        trade_id="trade-1",
        direction="long",
        entry_fill_at=observed_at,
        entry_fill_price=4800.0,
        exit_fill_at=bar_time,
        exit_fill_price=4810.0,
        net_pnl=62.5,
        bars_held=3,
        exit_reason="fixed_bars",
    )
    return StrategyDashboardViewModel(
        run_id="run-dashboard",
        source_dataset_ref="ES.c.0|ohlcv|1m|csv|fixture@1",
        strategy_model_id="high_vol_higher_low_fixed_exit",
        market_model_id="high_volatility",
        signal_model_id="higher_low_long",
        exit_model_id="fixed_bars",
        risk_model_id="fixed_quantity",
        simulation_assumptions_fingerprint="abc123",
        overview=StrategyDashboardOverviewKpis(
            net_pnl=Decimal("1250"),
            total_return=0.0125,
            max_drawdown=Decimal("-500"),
            current_drawdown=Decimal("-120"),
            sharpe_ratio=1.15,
            sortino_ratio=1.42,
            profit_factor=1.8,
            expectancy=Decimal("62.5"),
            trade_count=20,
            win_rate=0.55,
            avg_win=Decimal("180"),
            avg_loss=Decimal("-95"),
            total_costs=Decimal("40"),
        ),
        performance=StrategyDashboardPerformancePanels(
            monthly_pnl=(MonthlyPnlRow(month="2024-01", net_pnl=1250.0, trade_count=20),),
            trade_pnl_histogram=(
                TradePnlBucket(bucket_start=-100.0, bucket_end=0.0, count=8),
                TradePnlBucket(bucket_start=0.0, bucket_end=100.0, count=12),
            ),
            direction_breakdown=(
                DirectionBreakdownRow(
                    direction="long",
                    trade_count=15,
                    net_pnl=1000.0,
                    win_rate=0.6,
                ),
            ),
            session_breakdown=(
                SessionBreakdownRow(session="RTH", trade_count=12, net_pnl=900.0, win_rate=0.58),
            ),
            hour_breakdown=(
                HourBreakdownRow(hour_bucket="14:00", trade_count=5, net_pnl=300.0, win_rate=0.6),
            ),
            recent_trades=(trade,),
        ),
        metric_context=StrategyDashboardMetricContext(
            warnings=(
                StrategyDashboardMetricWarning(
                    code="LOW_SAMPLE_SIZE",
                    message="Only 20 trades — interpret cautiously.",
                ),
            ),
            sharpe_annualization="daily_equity_returns_sqrt_252",
            sample_eligible=False,
            min_recommended_trades=30,
        ),
        trades=(trade,),
        equity=(
            EquityPointRow(observed_at=observed_at, equity=100000.0, drawdown=0.0),
            EquityPointRow(observed_at=bar_time, equity=100062.5, drawdown=-120.0),
        ),
        bars=(
            OhlcvBarRow(
                observed_at=observed_at,
                open=4798.0,
                high=4802.0,
                low=4796.0,
                close=4800.0,
                volume=1200.0,
            ),
            OhlcvBarRow(
                observed_at=bar_time,
                open=4800.0,
                high=4812.0,
                low=4799.0,
                close=4810.0,
                volume=1500.0,
            ),
        ),
        metadata=StrategyDashboardMetadata(
            evaluation_timeframe="1m",
            bar_count=2,
            effective_from_utc=observed_at,
            effective_to_utc=bar_time,
        ),
    )


def test_render_strategy_research_dashboard_writes_html(tmp_path: Path) -> None:
    output = tmp_path / "strategy_dashboard.html"
    path = render_strategy_research_dashboard(_sample_view_model(), output)

    assert path == output
    content = output.read_text(encoding="utf-8")
    assert "Strategy Research dashboard — run-dashboard" in content
    assert "Interpretation warnings" in content
    assert "LOW_SAMPLE_SIZE" in content
    assert "Net PnL" in content
    assert "Profit Factor" in content
    assert "lightweight-charts" in content
    assert "chart-ohlcv" in content
    assert "recent-trades-table" in content
    assert "focusTradeRange" in content
    assert '"run_id": "run-dashboard"' in content


def test_render_strategy_research_dashboard_embeds_bars_for_chart(tmp_path: Path) -> None:
    output = tmp_path / "strategy_dashboard.html"
    render_strategy_research_dashboard(_sample_view_model(), output)
    content = output.read_text(encoding="utf-8")
    assert '"close": 4810.0' in content
    assert "trade-1" in content
