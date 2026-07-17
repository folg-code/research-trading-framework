"""Helpers for the Strategy Research dashboard page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa

from dashboard_app.catalog import list_runs
from dashboard_app.contracts import (
    PRESENTATION_SCHEMA_VERSION,
    ChartWindow,
    RunSummary,
    TradeView,
    WorkflowKind,
)
from dashboard_app.query import DashboardQueryService, OhlcvWindowResult

_DEFAULT_PAD = timedelta(hours=2)
_DEFAULT_MAX_BARS = 1_500


@dataclass(frozen=True, slots=True)
class StrategyRunArtifacts:
    """Loaded artifacts for one strategy research run."""

    summary: RunSummary
    metrics: dict[str, Any] | None
    equity: pa.Table
    trades: pa.Table


def list_strategy_runs(storage_root: Path) -> tuple[RunSummary, ...]:
    """Return STRATEGY catalog rows newest-first."""
    catalog = list_runs(storage_root)
    return tuple(item for item in catalog.runs if item.workflow is WorkflowKind.STRATEGY)


def load_strategy_run(
    service: DashboardQueryService,
    summary: RunSummary,
) -> StrategyRunArtifacts:
    """Load KPI metrics, equity and trades for one catalog row."""
    run_dir = Path(summary.storage_path)
    metrics_table = service.read_parquet_columns(run_dir / "analytics" / "summary_metrics.parquet")
    metrics: dict[str, Any] | None = None
    if metrics_table.num_rows > 0:
        metrics = {
            name: metrics_table.column(name)[0].as_py() for name in metrics_table.column_names
        }
    return StrategyRunArtifacts(
        summary=summary,
        metrics=metrics,
        equity=service.read_strategy_equity(run_dir),
        trades=service.read_strategy_trades(run_dir),
    )


def trades_to_views(trades: pa.Table) -> tuple[TradeView, ...]:
    """Map strategy trades.parquet rows to presentation TradeView DTOs."""
    if trades.num_rows == 0:
        return ()
    required = {
        "trade_id",
        "direction",
        "entry_fill_at",
        "exit_fill_at",
        "entry_fill_price",
        "exit_fill_price",
        "quantity",
        "net_pnl",
        "bars_held",
    }
    missing = required - set(trades.column_names)
    if missing:
        msg = f"trades.parquet missing columns: {sorted(missing)}"
        raise ValueError(msg)

    views: list[TradeView] = []
    for index in range(trades.num_rows):
        entry_at = _as_utc(trades.column("entry_fill_at")[index].as_py())
        exit_at = _as_utc(trades.column("exit_fill_at")[index].as_py())
        views.append(
            TradeView(
                schema_version=PRESENTATION_SCHEMA_VERSION,
                trade_id=str(trades.column("trade_id")[index].as_py()),
                side=str(trades.column("direction")[index].as_py()),
                entry_at_utc=entry_at,
                exit_at_utc=exit_at,
                entry_price=_optional_float(trades.column("entry_fill_price")[index].as_py()),
                exit_price=_optional_float(trades.column("exit_fill_price")[index].as_py()),
                quantity=_optional_float(trades.column("quantity")[index].as_py()),
                pnl=_optional_float(trades.column("net_pnl")[index].as_py()),
                bars_held=_optional_int(trades.column("bars_held")[index].as_py()),
            )
        )
    return tuple(views)


def chart_window_for_trade(
    trade: TradeView,
    *,
    timeframe: str,
    pad: timedelta = _DEFAULT_PAD,
    max_bars: int = _DEFAULT_MAX_BARS,
) -> ChartWindow:
    """Build a bounded ChartWindow around one trade's entry/exit fills."""
    end = trade.entry_at_utc + pad if trade.exit_at_utc is None else trade.exit_at_utc + pad
    start = trade.entry_at_utc - pad
    return ChartWindow(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        start_at_utc=start,
        end_at_utc=end,
        timeframe=timeframe,
        max_bars=max_bars,
    )


def load_trade_chart_window(
    service: DashboardQueryService,
    *,
    dataset_ref: str,
    trade: TradeView,
    timeframe: str,
) -> OhlcvWindowResult:
    """Load windowed OHLCV for one selected trade."""
    window = chart_window_for_trade(trade, timeframe=timeframe)
    return service.read_ohlcv_window(dataset_ref=dataset_ref, window=window)


def _as_utc(value: Any) -> datetime:
    if not isinstance(value, datetime):
        msg = f"expected datetime, got {type(value)!r}"
        raise TypeError(msg)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
