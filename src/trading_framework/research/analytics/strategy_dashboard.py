"""Strategy Research dashboard view model — presentation types and serialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

import polars as pl

from trading_framework.market.models import MarketBar

DashboardSection = Literal["overview", "performance", "conditional"]


@dataclass(frozen=True, slots=True)
class OhlcvBarRow:
    """One OHLCV bar for dashboard chart rendering."""

    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class TradeMarkerRow:
    """One simulated trade for dashboard table and chart markers."""

    trade_id: str
    direction: str
    entry_fill_at: datetime
    entry_fill_price: float
    exit_fill_at: datetime
    exit_fill_price: float
    net_pnl: float
    bars_held: int
    exit_reason: str


@dataclass(frozen=True, slots=True)
class EquityPointRow:
    """One equity snapshot for dashboard equity and drawdown panes."""

    observed_at: datetime
    equity: float
    drawdown: float


@dataclass(frozen=True, slots=True)
class StrategyDashboardOverviewKpis:
    """Twelve primary KPI cards for the Overview section."""

    net_pnl: Decimal
    total_return: float | None
    max_drawdown: Decimal
    current_drawdown: Decimal
    sharpe_ratio: float | None
    sortino_ratio: float | None
    profit_factor: float | None
    expectancy: Decimal | None
    trade_count: int
    win_rate: float | None
    avg_win: Decimal | None
    avg_loss: Decimal | None
    total_costs: Decimal


@dataclass(frozen=True, slots=True)
class MonthlyPnlRow:
    """Monthly aggregated trade PnL."""

    month: str
    net_pnl: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class TradePnlBucket:
    """One histogram bucket over trade net PnL."""

    bucket_start: float
    bucket_end: float
    count: int


@dataclass(frozen=True, slots=True)
class DirectionBreakdownRow:
    """Conditional performance for one direction label."""

    direction: str
    trade_count: int
    net_pnl: float
    win_rate: float | None


@dataclass(frozen=True, slots=True)
class SessionBreakdownRow:
    """Conditional performance for one session bucket."""

    session: str
    trade_count: int
    net_pnl: float
    win_rate: float | None


@dataclass(frozen=True, slots=True)
class HourBreakdownRow:
    """Conditional performance for one hour-of-day bucket."""

    hour_bucket: str
    trade_count: int
    net_pnl: float
    win_rate: float | None


@dataclass(frozen=True, slots=True)
class StrategyDashboardPerformancePanels:
    """Performance Analysis and Conditional Analysis chart payloads."""

    monthly_pnl: tuple[MonthlyPnlRow, ...]
    trade_pnl_histogram: tuple[TradePnlBucket, ...]
    direction_breakdown: tuple[DirectionBreakdownRow, ...]
    session_breakdown: tuple[SessionBreakdownRow, ...]
    hour_breakdown: tuple[HourBreakdownRow, ...]
    recent_trades: tuple[TradeMarkerRow, ...]


@dataclass(frozen=True, slots=True)
class StrategyDashboardMetricWarning:
    """Context warning shown next to KPI cards and charts."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class StrategyDashboardMetricContext:
    """Interpretation context and eligibility flags for dashboard metrics."""

    warnings: tuple[StrategyDashboardMetricWarning, ...]
    sharpe_annualization: str | None
    sample_eligible: bool
    min_recommended_trades: int


@dataclass(frozen=True, slots=True)
class StrategyDashboardMetadata:
    """Dashboard metadata describing loaded bar coverage."""

    evaluation_timeframe: str
    bar_count: int
    effective_from_utc: datetime | None
    effective_to_utc: datetime | None


@dataclass(frozen=True, slots=True)
class StrategyDashboardViewModel:
    """Ephemeral JSON-serializable dashboard payload for one Strategy Research run."""

    run_id: str
    source_dataset_ref: str
    strategy_model_id: str
    market_model_id: str
    signal_model_id: str
    exit_model_id: str
    risk_model_id: str
    simulation_assumptions_fingerprint: str
    overview: StrategyDashboardOverviewKpis
    performance: StrategyDashboardPerformancePanels
    metric_context: StrategyDashboardMetricContext
    trades: tuple[TradeMarkerRow, ...]
    equity: tuple[EquityPointRow, ...]
    bars: tuple[OhlcvBarRow, ...]
    metadata: StrategyDashboardMetadata


def market_bars_to_rows(bars: list[MarketBar]) -> tuple[OhlcvBarRow, ...]:
    """Convert canonical market bars to dashboard OHLCV rows."""
    return tuple(
        OhlcvBarRow(
            observed_at=bar.observed_at,
            open=float(bar.open.value),
            high=float(bar.high.value),
            low=float(bar.low.value),
            close=float(bar.close.value),
            volume=float(bar.volume.value),
        )
        for bar in bars
    )


def trades_dataframe_to_rows(trades: pl.DataFrame) -> tuple[TradeMarkerRow, ...]:
    """Convert persisted trades facts to dashboard marker rows."""
    if len(trades) == 0:
        return ()
    rows: list[TradeMarkerRow] = []
    for row in trades.sort("exit_fill_at", descending=True).iter_rows(named=True):
        rows.append(
            TradeMarkerRow(
                trade_id=str(row["trade_id"]),
                direction=str(row["direction"]),
                entry_fill_at=row["entry_fill_at"],
                entry_fill_price=float(row["entry_fill_price"]),
                exit_fill_at=row["exit_fill_at"],
                exit_fill_price=float(row["exit_fill_price"]),
                net_pnl=float(row["net_pnl"]),
                bars_held=int(row["bars_held"]),
                exit_reason=str(row["exit_reason"]),
            )
        )
    return tuple(rows)


def equity_dataframe_to_rows(equity: pl.DataFrame) -> tuple[EquityPointRow, ...]:
    """Convert persisted equity facts to dashboard equity rows."""
    if len(equity) == 0:
        return ()
    rows: list[EquityPointRow] = []
    for row in equity.sort("observed_at").iter_rows(named=True):
        rows.append(
            EquityPointRow(
                observed_at=row["observed_at"],
                equity=float(row["equity"]),
                drawdown=float(row["drawdown"]),
            )
        )
    return tuple(rows)


def effective_equity_range(equity: pl.DataFrame) -> tuple[datetime | None, datetime | None]:
    """Return the simulated period bounds from equity observations."""
    if len(equity) == 0:
        return None, None
    ordered = equity.sort("observed_at")
    start = ordered.row(0, named=True)["observed_at"]
    end = ordered.row(-1, named=True)["observed_at"]
    return start, end


def strategy_dashboard_view_model_to_dict(view_model: StrategyDashboardViewModel) -> dict[str, Any]:
    """Serialize a dashboard view model to JSON-compatible primitives."""
    return {
        "run_id": view_model.run_id,
        "source_dataset_ref": view_model.source_dataset_ref,
        "strategy_model_id": view_model.strategy_model_id,
        "market_model_id": view_model.market_model_id,
        "signal_model_id": view_model.signal_model_id,
        "exit_model_id": view_model.exit_model_id,
        "risk_model_id": view_model.risk_model_id,
        "simulation_assumptions_fingerprint": view_model.simulation_assumptions_fingerprint,
        "sections": {
            "overview": _overview_to_dict(view_model.overview),
            "performance": _performance_to_dict(view_model.performance),
            "conditional": _conditional_to_dict(
                view_model.performance,
                market_model_id=view_model.market_model_id,
                signal_model_id=view_model.signal_model_id,
            ),
        },
        "metric_context": _metric_context_to_dict(view_model.metric_context),
        "trades": [_trade_marker_to_dict(row) for row in view_model.trades],
        "equity": [_equity_point_to_dict(row) for row in view_model.equity],
        "bars": [_ohlcv_bar_to_dict(row) for row in view_model.bars],
        "metadata": _metadata_to_dict(view_model.metadata),
    }


def _overview_to_dict(overview: StrategyDashboardOverviewKpis) -> dict[str, Any]:
    return {
        "net_pnl": str(overview.net_pnl),
        "total_return": overview.total_return,
        "max_drawdown": str(overview.max_drawdown),
        "current_drawdown": str(overview.current_drawdown),
        "sharpe_ratio": overview.sharpe_ratio,
        "sortino_ratio": overview.sortino_ratio,
        "profit_factor": overview.profit_factor,
        "expectancy": (str(overview.expectancy) if overview.expectancy is not None else None),
        "trade_count": overview.trade_count,
        "win_rate": overview.win_rate,
        "avg_win": str(overview.avg_win) if overview.avg_win is not None else None,
        "avg_loss": str(overview.avg_loss) if overview.avg_loss is not None else None,
        "total_costs": str(overview.total_costs),
    }


def _performance_to_dict(performance: StrategyDashboardPerformancePanels) -> dict[str, Any]:
    return {
        "monthly_pnl": [
            {
                "month": row.month,
                "net_pnl": row.net_pnl,
                "trade_count": row.trade_count,
            }
            for row in performance.monthly_pnl
        ],
        "trade_pnl_histogram": [
            {
                "bucket_start": row.bucket_start,
                "bucket_end": row.bucket_end,
                "count": row.count,
            }
            for row in performance.trade_pnl_histogram
        ],
        "recent_trades": [_trade_marker_to_dict(row) for row in performance.recent_trades],
    }


def _conditional_to_dict(
    performance: StrategyDashboardPerformancePanels,
    *,
    market_model_id: str,
    signal_model_id: str,
) -> dict[str, Any]:
    return {
        "direction_breakdown": [
            {
                "direction": row.direction,
                "trade_count": row.trade_count,
                "net_pnl": row.net_pnl,
                "win_rate": row.win_rate,
            }
            for row in performance.direction_breakdown
        ],
        "session_breakdown": [
            {
                "session": row.session,
                "trade_count": row.trade_count,
                "net_pnl": row.net_pnl,
                "win_rate": row.win_rate,
            }
            for row in performance.session_breakdown
        ],
        "hour_breakdown": [
            {
                "hour_bucket": row.hour_bucket,
                "trade_count": row.trade_count,
                "net_pnl": row.net_pnl,
                "win_rate": row.win_rate,
            }
            for row in performance.hour_breakdown
        ],
        "market_model_id": market_model_id,
        "signal_model_id": signal_model_id,
        "volatility_regime": None,
    }


def _metric_context_to_dict(context: StrategyDashboardMetricContext) -> dict[str, Any]:
    return {
        "warnings": [
            {"code": warning.code, "message": warning.message} for warning in context.warnings
        ],
        "sharpe_annualization": context.sharpe_annualization,
        "sample_eligible": context.sample_eligible,
        "min_recommended_trades": context.min_recommended_trades,
    }


def _trade_marker_to_dict(row: TradeMarkerRow) -> dict[str, Any]:
    return {
        "trade_id": row.trade_id,
        "direction": row.direction,
        "entry_fill_at": row.entry_fill_at.isoformat(),
        "entry_fill_price": row.entry_fill_price,
        "exit_fill_at": row.exit_fill_at.isoformat(),
        "exit_fill_price": row.exit_fill_price,
        "net_pnl": row.net_pnl,
        "bars_held": row.bars_held,
        "exit_reason": row.exit_reason,
    }


def _equity_point_to_dict(row: EquityPointRow) -> dict[str, Any]:
    return {
        "observed_at": row.observed_at.isoformat(),
        "equity": row.equity,
        "drawdown": row.drawdown,
    }


def _ohlcv_bar_to_dict(row: OhlcvBarRow) -> dict[str, Any]:
    return {
        "observed_at": row.observed_at.isoformat(),
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }


def _metadata_to_dict(metadata: StrategyDashboardMetadata) -> dict[str, Any]:
    return {
        "evaluation_timeframe": metadata.evaluation_timeframe,
        "bar_count": metadata.bar_count,
        "effective_from_utc": (
            metadata.effective_from_utc.isoformat()
            if metadata.effective_from_utc is not None
            else None
        ),
        "effective_to_utc": (
            metadata.effective_to_utc.isoformat() if metadata.effective_to_utc is not None else None
        ),
    }
