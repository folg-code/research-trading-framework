"""Plotly chart builders for the dashboard app."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation

import plotly.graph_objects as go
import pyarrow as pa
from plotly.subplots import make_subplots

from dashboard_app.charts.overlays import DEFAULT_OVERLAY_REGISTRY, OverlayKind, OverlayRegistry
from dashboard_app.contracts import TradeView
from dashboard_app.query import OhlcvBarRow


def build_equity_drawdown_figure(equity: pa.Table) -> go.Figure:
    """Build equity + drawdown dual-pane figure from equity.parquet."""
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.65, 0.35],
        subplot_titles=("Equity", "Drawdown"),
    )
    if equity.num_rows == 0 or "observed_at" not in equity.column_names:
        figure.update_layout(height=420, margin={"l": 40, "r": 20, "t": 40, "b": 30})
        return figure

    xs = [value.as_py() for value in equity.column("observed_at")]
    equity_ys = [float(value.as_py()) for value in equity.column("equity")]
    drawdown_ys = [float(value.as_py()) for value in equity.column("drawdown")]
    figure.add_trace(go.Scatter(x=xs, y=equity_ys, name="equity", mode="lines"), row=1, col=1)
    figure.add_trace(
        go.Scatter(x=xs, y=drawdown_ys, name="drawdown", mode="lines", fill="tozeroy"),
        row=2,
        col=1,
    )
    figure.update_layout(height=480, margin={"l": 40, "r": 20, "t": 40, "b": 30}, showlegend=False)
    return figure


def build_walk_forward_fold_figure(folds: pa.Table) -> go.Figure:
    """Build grouped IS vs OOS net-PnL bars from walk_forward_folds.parquet."""
    figure = go.Figure()
    required = {"fold_index", "train_net_pnl", "oos_net_pnl"}
    if folds.num_rows == 0 or not required.issubset(folds.column_names):
        figure.update_layout(
            title="Walk-forward IS vs OOS net PnL",
            height=360,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
        )
        return figure

    rows = sorted(
        (
            (
                int(folds.column("fold_index")[index].as_py()),
                _label_for_fold(
                    fold_index=int(folds.column("fold_index")[index].as_py()),
                    fold_id=(
                        folds.column("fold_id")[index].as_py()
                        if "fold_id" in folds.column_names
                        else None
                    ),
                ),
                _numeric_metric(folds.column("train_net_pnl")[index].as_py()),
                _numeric_metric(folds.column("oos_net_pnl")[index].as_py()),
            )
            for index in range(folds.num_rows)
        ),
        key=lambda item: item[0],
    )
    labels = [label for _, label, _, _ in rows]
    train_values = [train for _, _, train, _ in rows]
    oos_values = [oos for _, _, _, oos in rows]

    figure.add_trace(
        go.Bar(
            x=labels,
            y=train_values,
            name="Training (IS)",
            marker_color="#4C78A8",
        )
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=oos_values,
            name="Unseen (OOS)",
            marker_color="#F58518",
        )
    )
    figure.update_layout(
        title="Walk-forward IS vs OOS net PnL by fold",
        barmode="group",
        height=420,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        yaxis_title="Net PnL",
        xaxis_title="Fold",
    )
    return figure


def _label_for_fold(*, fold_index: int, fold_id: object) -> str:
    if isinstance(fold_id, str) and fold_id.strip():
        return fold_id.strip()
    return f"Fold {fold_index + 1}"


def _numeric_metric(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(Decimal(text))
        except (InvalidOperation, ValueError):
            return None
    return None


def build_ohlcv_trade_figure(
    bars: Sequence[OhlcvBarRow],
    trade: TradeView,
    *,
    registry: OverlayRegistry | None = None,
) -> go.Figure:
    """Build candlestick chart with entry/exit markers and trade connection."""
    overlay_registry = registry or DEFAULT_OVERLAY_REGISTRY
    figure = go.Figure()
    if bars:
        figure.add_trace(
            go.Candlestick(
                x=[bar.observed_at_utc for bar in bars],
                open=[bar.open for bar in bars],
                high=[bar.high for bar in bars],
                low=[bar.low for bar in bars],
                close=[bar.close for bar in bars],
                name="OHLCV",
            )
        )

    if trade.entry_price is not None:
        overlay_registry.apply(
            figure,
            OverlayKind.MARKERS,
            {
                "x": [trade.entry_at_utc],
                "y": [trade.entry_price],
                "text": [f"entry {trade.side}"],
                "name": "entry",
                "symbol": "triangle-up",
                "color": "#2ca02c",
            },
        )
    if trade.exit_at_utc is not None and trade.exit_price is not None:
        overlay_registry.apply(
            figure,
            OverlayKind.MARKERS,
            {
                "x": [trade.exit_at_utc],
                "y": [trade.exit_price],
                "text": ["exit"],
                "name": "exit",
                "symbol": "triangle-down",
                "color": "#d62728",
            },
        )
        if trade.entry_price is not None:
            overlay_registry.apply(
                figure,
                OverlayKind.TRADE_CONNECTION,
                {
                    "x": [trade.entry_at_utc, trade.exit_at_utc],
                    "y": [trade.entry_price, trade.exit_price],
                    "name": "trade link",
                },
            )

    figure.update_layout(
        height=520,
        margin={"l": 40, "r": 20, "t": 30, "b": 30},
        xaxis_rangeslider_visible=False,
        title=f"Trade {trade.trade_id}",
    )
    return figure
