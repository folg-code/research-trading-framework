"""Compute Strategy Research dashboard metrics from persisted facts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import polars as pl

from trading_framework.research.analytics.strategy_dashboard import (
    DirectionBreakdownRow,
    HourBreakdownRow,
    MonthlyPnlRow,
    SessionBreakdownRow,
    StrategyDashboardMetricContext,
    StrategyDashboardMetricWarning,
    StrategyDashboardOverviewKpis,
    StrategyDashboardPerformancePanels,
    TradeMarkerRow,
    TradePnlBucket,
)
from trading_framework.research.analytics.strategy_summarize import (
    StrategyRunSummary,
    summarize_strategy_run,
)
from trading_framework.time.sessions import CmeEsRthSessionResolver
from trading_framework.time.sessions.constants import ES_RTH_SESSION_ID

_MIN_RECOMMENDED_TRADES = 30
_SHARPE_ANNUALIZATION_FACTOR = math.sqrt(252)
_RECENT_TRADES_LIMIT = 20
_HISTOGRAM_BUCKET_COUNT = 12


@dataclass(frozen=True, slots=True)
class StrategyDashboardAnalytics:
    """Computed dashboard analytics for one persisted Strategy Research run."""

    overview: StrategyDashboardOverviewKpis
    performance: StrategyDashboardPerformancePanels
    metric_context: StrategyDashboardMetricContext


def compute_strategy_dashboard_analytics(
    *,
    trades: pl.DataFrame,
    equity: pl.DataFrame,
    evaluation_timeframe: str,
    recent_trade_rows: tuple[TradeMarkerRow, ...],
) -> StrategyDashboardAnalytics:
    """Compute overview KPIs, performance panels and metric context warnings."""
    run_summary = summarize_strategy_run(trades=trades, equity=equity)
    initial_equity = _initial_equity(equity)
    current_drawdown = _current_drawdown(equity)
    sharpe_ratio, sortino_ratio = _compute_sharpe_and_sortino(equity)

    overview = _build_overview_kpis(
        run_summary=run_summary,
        trades=trades,
        initial_equity=initial_equity,
        current_drawdown=current_drawdown,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
    )
    performance = StrategyDashboardPerformancePanels(
        monthly_pnl=_monthly_pnl_rows(trades),
        trade_pnl_histogram=_trade_pnl_histogram(trades),
        direction_breakdown=_direction_breakdown(trades),
        session_breakdown=_session_breakdown(trades),
        hour_breakdown=_hour_breakdown(trades),
        recent_trades=recent_trade_rows[:_RECENT_TRADES_LIMIT],
    )
    metric_context = _build_metric_context(
        trades=trades,
        equity=equity,
        overview=overview,
        evaluation_timeframe=evaluation_timeframe,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
    )
    return StrategyDashboardAnalytics(
        overview=overview,
        performance=performance,
        metric_context=metric_context,
    )


def _build_overview_kpis(
    *,
    run_summary: StrategyRunSummary,
    trades: pl.DataFrame,
    initial_equity: Decimal,
    current_drawdown: Decimal,
    sharpe_ratio: float | None,
    sortino_ratio: float | None,
) -> StrategyDashboardOverviewKpis:
    total_return = _total_return(
        initial_equity=initial_equity,
        final_equity=run_summary.final_equity,
    )
    profit_factor = _profit_factor(trades)
    expectancy = _expectancy(trades)
    avg_win, avg_loss = _average_win_loss(trades)

    return StrategyDashboardOverviewKpis(
        net_pnl=run_summary.net_pnl,
        total_return=total_return,
        max_drawdown=run_summary.max_drawdown,
        current_drawdown=current_drawdown,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        profit_factor=profit_factor,
        expectancy=expectancy,
        trade_count=run_summary.trade_count,
        win_rate=run_summary.win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        total_costs=run_summary.total_commission,
    )


def _build_metric_context(
    *,
    trades: pl.DataFrame,
    equity: pl.DataFrame,
    overview: StrategyDashboardOverviewKpis,
    evaluation_timeframe: str,
    sharpe_ratio: float | None,
    sortino_ratio: float | None,
) -> StrategyDashboardMetricContext:
    warnings: list[StrategyDashboardMetricWarning] = []
    trade_count = overview.trade_count
    sample_eligible = trade_count >= _MIN_RECOMMENDED_TRADES

    if trade_count < _MIN_RECOMMENDED_TRADES:
        warnings.append(
            StrategyDashboardMetricWarning(
                code="LOW_SAMPLE_SIZE",
                message=(
                    f"Only {trade_count} trades — interpret win rate, profit factor and "
                    f"expectancy cautiously; recommended minimum is {_MIN_RECOMMENDED_TRADES}."
                ),
            )
        )
    if (
        overview.win_rate is not None
        and overview.avg_win is not None
        and overview.avg_loss is not None
        and overview.avg_loss != 0
        and abs(overview.avg_loss) > Decimal("0")
    ):
        payoff = float(overview.avg_win / abs(overview.avg_loss))
        if payoff < 1.0 and overview.win_rate > 0.5:
            warnings.append(
                StrategyDashboardMetricWarning(
                    code="WIN_RATE_WITHOUT_PAYOFF",
                    message=(
                        "Win rate exceeds 50% but average win is smaller than average loss "
                        f"(payoff ratio {payoff:.2f})."
                    ),
                )
            )
    if sharpe_ratio is not None or sortino_ratio is not None:
        warnings.append(
            StrategyDashboardMetricWarning(
                code="SHARPE_ANNUALIZATION",
                message=(
                    "Sharpe and Sortino use daily equity returns annualized with sqrt(252); "
                    f"bar timeframe is {evaluation_timeframe}."
                ),
            )
        )
    if overview.total_return is not None:
        days = _effective_trading_days(equity)
        if days is not None and days < 60:
            warnings.append(
                StrategyDashboardMetricWarning(
                    code="SHORT_BACKTEST_PERIOD",
                    message=(
                        f"Total return covers about {days} calendar days — avoid CAGR-style "
                        "interpretation on short samples."
                    ),
                )
            )
    if overview.max_drawdown < 0:
        warnings.append(
            StrategyDashboardMetricWarning(
                code="DRAWDOWN_WITHOUT_DURATION",
                message=(
                    "Max drawdown is shown without underwater duration; use the drawdown "
                    "curve for timing context."
                ),
            )
        )
    warnings.append(
        StrategyDashboardMetricWarning(
            code="COST_ASSUMPTIONS",
            message=(
                "Total costs reflect persisted commission fields only; verify slippage and "
                "fill assumptions in the run manifest fingerprint."
            ),
        )
    )
    if trade_count == 0:
        warnings.append(
            StrategyDashboardMetricWarning(
                code="NO_TRADES",
                message="No completed trades in this run — trade-conditioned panels are empty.",
            )
        )

    return StrategyDashboardMetricContext(
        warnings=tuple(warnings),
        sharpe_annualization="daily_equity_returns_sqrt_252",
        sample_eligible=sample_eligible,
        min_recommended_trades=_MIN_RECOMMENDED_TRADES,
    )


def _initial_equity(equity: pl.DataFrame) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    ordered = equity.sort("observed_at")
    return Decimal(str(ordered.row(0, named=True)["equity"]))


def _current_drawdown(equity: pl.DataFrame) -> Decimal:
    if len(equity) == 0:
        return Decimal("0")
    ordered = equity.sort("observed_at")
    return Decimal(str(ordered.row(-1, named=True)["drawdown"]))


def _total_return(*, initial_equity: Decimal, final_equity: Decimal) -> float | None:
    if initial_equity <= 0:
        return None
    return float((final_equity - initial_equity) / initial_equity)


def _profit_factor(trades: pl.DataFrame) -> float | None:
    if len(trades) == 0:
        return None
    gross_pnls = trades.get_column("gross_pnl")
    gross_wins = float(gross_pnls.filter(gross_pnls > 0).sum())
    gross_losses = float(gross_pnls.filter(gross_pnls < 0).sum())
    if gross_losses == 0.0:
        return None
    return gross_wins / abs(gross_losses)


def _expectancy(trades: pl.DataFrame) -> Decimal | None:
    if len(trades) == 0:
        return None
    return Decimal(str(trades.get_column("net_pnl").mean()))


def _average_win_loss(trades: pl.DataFrame) -> tuple[Decimal | None, Decimal | None]:
    if len(trades) == 0:
        return None, None
    net_pnls = trades.get_column("net_pnl")
    winning = net_pnls.filter(net_pnls > 0)
    losing = net_pnls.filter(net_pnls < 0)
    avg_win = Decimal(str(winning.mean())) if len(winning) > 0 else None
    avg_loss = Decimal(str(losing.mean())) if len(losing) > 0 else None
    return avg_win, avg_loss


def _compute_sharpe_and_sortino(equity: pl.DataFrame) -> tuple[float | None, float | None]:
    daily_returns = _daily_equity_returns(equity)
    if daily_returns is None or len(daily_returns) < 2:
        return None, None

    mean_return = float(daily_returns.mean())  # type: ignore[arg-type]
    std_return = float(daily_returns.std())  # type: ignore[arg-type]
    sharpe = None if std_return == 0.0 else mean_return / std_return * _SHARPE_ANNUALIZATION_FACTOR

    downside = daily_returns.filter(daily_returns < 0)
    if len(downside) < 2:
        sortino = None
    else:
        downside_std = float(downside.std())  # type: ignore[arg-type]
        sortino = (
            None
            if downside_std == 0.0
            else mean_return / downside_std * _SHARPE_ANNUALIZATION_FACTOR
        )
    return sharpe, sortino


def _daily_equity_returns(equity: pl.DataFrame) -> pl.Series | None:
    if len(equity) < 2:
        return None
    daily_equity = (
        equity.sort("observed_at")
        .with_columns(pl.col("observed_at").dt.date().alias("trade_date"))
        .group_by("trade_date")
        .agg(pl.col("equity").last())
        .sort("trade_date")
    )
    if len(daily_equity) < 2:
        return None
    returns = daily_equity.with_columns(pl.col("equity").pct_change().alias("daily_return"))
    series = returns.get_column("daily_return").drop_nulls()
    if len(series) == 0:
        return None
    return series


def _monthly_pnl_rows(trades: pl.DataFrame) -> tuple[MonthlyPnlRow, ...]:
    if len(trades) == 0:
        return ()
    grouped = (
        trades.with_columns(pl.col("exit_fill_at").dt.strftime("%Y-%m").alias("month"))
        .group_by("month")
        .agg(
            pl.col("net_pnl").sum().alias("net_pnl"),
            pl.len().alias("trade_count"),
        )
        .sort("month")
    )
    return tuple(
        MonthlyPnlRow(
            month=str(row["month"]),
            net_pnl=float(row["net_pnl"]),
            trade_count=int(row["trade_count"]),
        )
        for row in grouped.iter_rows(named=True)
    )


def _trade_pnl_histogram(trades: pl.DataFrame) -> tuple[TradePnlBucket, ...]:
    if len(trades) == 0:
        return ()
    net_pnls = trades.get_column("net_pnl").to_list()
    minimum = float(min(net_pnls))
    maximum = float(max(net_pnls))
    if minimum == maximum:
        return (TradePnlBucket(bucket_start=minimum, bucket_end=maximum, count=len(net_pnls)),)

    width = (maximum - minimum) / _HISTOGRAM_BUCKET_COUNT
    buckets = [
        TradePnlBucket(
            bucket_start=minimum + index * width,
            bucket_end=minimum + (index + 1) * width,
            count=0,
        )
        for index in range(_HISTOGRAM_BUCKET_COUNT)
    ]
    for value in net_pnls:
        index = min(int((float(value) - minimum) / width), _HISTOGRAM_BUCKET_COUNT - 1)
        bucket = buckets[index]
        buckets[index] = TradePnlBucket(
            bucket_start=bucket.bucket_start,
            bucket_end=bucket.bucket_end,
            count=bucket.count + 1,
        )
    return tuple(buckets)


def _direction_breakdown(trades: pl.DataFrame) -> tuple[DirectionBreakdownRow, ...]:
    if len(trades) == 0:
        return ()
    rows: list[DirectionBreakdownRow] = []
    for direction in sorted(trades.get_column("direction").unique().to_list()):
        subset = trades.filter(pl.col("direction") == direction)
        rows.append(_breakdown_row(subset=subset, label=str(direction)))
    return tuple(rows)


def _session_breakdown(trades: pl.DataFrame) -> tuple[SessionBreakdownRow, ...]:
    if len(trades) == 0:
        return ()
    enriched = _with_rth_membership(trades, timestamp_column="exit_fill_at")
    rows: list[SessionBreakdownRow] = []
    for session in ("RTH", "OUTSIDE_RTH"):
        subset = enriched.filter(pl.col("rth_membership") == session)
        if len(subset) == 0:
            continue
        breakdown = _breakdown_row(subset=subset, label=session)
        rows.append(
            SessionBreakdownRow(
                session=session,
                trade_count=breakdown.trade_count,
                net_pnl=breakdown.net_pnl,
                win_rate=breakdown.win_rate,
            )
        )
    return tuple(rows)


def _hour_breakdown(trades: pl.DataFrame) -> tuple[HourBreakdownRow, ...]:
    if len(trades) == 0:
        return ()
    enriched = trades.with_columns(
        pl.col("exit_fill_at")
        .dt.convert_time_zone("America/New_York")
        .dt.truncate("1h")
        .dt.strftime("%H:00")
        .alias("hour_bucket")
    )
    rows: list[HourBreakdownRow] = []
    for hour_bucket in sorted(enriched.get_column("hour_bucket").unique().to_list()):
        subset = enriched.filter(pl.col("hour_bucket") == hour_bucket)
        breakdown = _breakdown_row(subset=subset, label=str(hour_bucket))
        rows.append(
            HourBreakdownRow(
                hour_bucket=str(hour_bucket),
                trade_count=breakdown.trade_count,
                net_pnl=breakdown.net_pnl,
                win_rate=breakdown.win_rate,
            )
        )
    return tuple(rows)


def _breakdown_row(*, subset: pl.DataFrame, label: str) -> DirectionBreakdownRow:
    trade_count = len(subset)
    net_pnl = float(subset.get_column("net_pnl").sum())
    wins = int((subset.get_column("net_pnl") > 0).sum())
    win_rate = None if trade_count == 0 else wins / trade_count
    return DirectionBreakdownRow(
        direction=label,
        trade_count=trade_count,
        net_pnl=net_pnl,
        win_rate=win_rate,
    )


def _with_rth_membership(frame: pl.DataFrame, *, timestamp_column: str) -> pl.DataFrame:
    timestamps = frame.get_column(timestamp_column)
    resolved = CmeEsRthSessionResolver().resolve(timestamps)
    membership = [
        "RTH" if session_id == ES_RTH_SESSION_ID else "OUTSIDE_RTH"
        for session_id in resolved["session_id"].to_list()
    ]
    return frame.with_columns(pl.Series("rth_membership", membership))


def _effective_trading_days(equity: pl.DataFrame) -> int | None:
    if len(equity) == 0:
        return None
    ordered = equity.sort("observed_at")
    start = ordered.row(0, named=True)["observed_at"]
    end = ordered.row(-1, named=True)["observed_at"]
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        return None
    return max((end.date() - start.date()).days, 1)
