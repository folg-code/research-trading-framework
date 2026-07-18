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


def build_parameter_sweep_surface_figure(
    heatmap: pa.Table,
    *,
    metric: str,
    x_axis: str,
    y_axis: str | None = None,
) -> go.Figure:
    """Build a 3D surface (2D axes) or 1D line chart from one heatmap slice."""
    figure = go.Figure()
    required = {"x_value", "value"}
    if heatmap.num_rows == 0 or not required.issubset(heatmap.column_names):
        figure.update_layout(
            title=f"{metric}: {x_axis}" + (f" x {y_axis}" if y_axis else ""),
            height=420,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
        )
        return figure

    if y_axis is None:
        return _build_one_axis_sweep_figure(heatmap, metric=metric, x_axis=x_axis)

    x_labels = _sorted_axis_labels(
        [heatmap.column("x_value")[index].as_py() for index in range(heatmap.num_rows)]
    )
    y_labels = _sorted_axis_labels(
        [
            heatmap.column("y_value")[index].as_py()
            for index in range(heatmap.num_rows)
            if "y_value" in heatmap.column_names
        ]
    )
    if not x_labels or not y_labels:
        return _build_one_axis_sweep_figure(heatmap, metric=metric, x_axis=x_axis)

    value_lookup: dict[tuple[str, str], float | None] = {}
    for index in range(heatmap.num_rows):
        x_label = _axis_label(heatmap.column("x_value")[index].as_py())
        y_label = _axis_label(
            heatmap.column("y_value")[index].as_py() if "y_value" in heatmap.column_names else None
        )
        if x_label is None or y_label is None:
            continue
        value_lookup[(x_label, y_label)] = _numeric_metric(heatmap.column("value")[index].as_py())

    z_grid = [
        [value_lookup.get((x_label, y_label)) for x_label in x_labels] for y_label in y_labels
    ]
    figure.add_trace(
        go.Surface(
            x=list(range(len(x_labels))),
            y=list(range(len(y_labels))),
            z=z_grid,
            colorscale="Viridis",
            colorbar={"title": metric},
            hovertemplate=(
                f"{x_axis}=%{{customdata[0]}}<br>"
                f"{y_axis}=%{{customdata[1]}}<br>"
                f"{metric}=%{{z}}<extra></extra>"
            ),
            customdata=[[[x_label, y_label] for x_label in x_labels] for y_label in y_labels],
        )
    )
    figure.update_layout(
        title=f"{metric}: {x_axis} x {y_axis}",
        height=520,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        scene={
            "xaxis": {
                "title": x_axis,
                "tickmode": "array",
                "tickvals": list(range(len(x_labels))),
                "ticktext": x_labels,
            },
            "yaxis": {
                "title": y_axis,
                "tickmode": "array",
                "tickvals": list(range(len(y_labels))),
                "ticktext": y_labels,
            },
            "zaxis": {"title": metric},
        },
    )
    return figure


def _build_one_axis_sweep_figure(
    heatmap: pa.Table,
    *,
    metric: str,
    x_axis: str,
) -> go.Figure:
    figure = go.Figure()
    points: dict[str, float | None] = {}
    for index in range(heatmap.num_rows):
        x_label = _axis_label(heatmap.column("x_value")[index].as_py())
        if x_label is None:
            continue
        points[x_label] = _numeric_metric(heatmap.column("value")[index].as_py())
    x_labels = _sorted_axis_labels(list(points))
    figure.add_trace(
        go.Scatter(
            x=x_labels,
            y=[points[label] for label in x_labels],
            mode="lines+markers",
            name=metric,
        )
    )
    figure.update_layout(
        title=f"{metric}: {x_axis}",
        height=420,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        xaxis_title=x_axis,
        yaxis_title=metric,
    )
    return figure


def _axis_label(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _sorted_axis_labels(values: list[object]) -> list[str]:
    labels = [label for label in (_axis_label(value) for value in values) if label is not None]
    unique = list(dict.fromkeys(labels))
    numeric_pairs: list[tuple[float, str]] = []
    for label in unique:
        parsed = _numeric_metric(label)
        if parsed is None:
            return sorted(unique)
        numeric_pairs.append((parsed, label))
    return [label for _, label in sorted(numeric_pairs, key=lambda item: item[0])]


def build_stress_delta_figure(stress: pa.Table) -> go.Figure:
    """Build stress-test delta net-PnL bars from stress_comparison.parquet."""
    figure = go.Figure()
    required = {"scenario_id", "delta_net_pnl"}
    if stress.num_rows == 0 or not required.issubset(stress.column_names):
        figure.update_layout(
            title="Stress delta vs baseline",
            height=360,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
        )
        return figure

    labels: list[str] = []
    deltas: list[float | None] = []
    colors: list[str] = []
    for index in range(stress.num_rows):
        scenario = stress.column("scenario_id")[index].as_py()
        label = _stress_scenario_label(scenario)
        delta = _numeric_metric(stress.column("delta_net_pnl")[index].as_py())
        labels.append(label)
        deltas.append(delta)
        if delta is None:
            colors.append("#9e9e9e")
        elif delta < 0:
            colors.append("#d62728")
        else:
            colors.append("#2ca02c")

    figure.add_trace(
        go.Bar(
            x=labels,
            y=deltas,
            marker_color=colors,
            name="delta net PnL",
        )
    )
    figure.update_layout(
        title="Stress delta vs baseline",
        height=420,
        margin={"l": 40, "r": 20, "t": 50, "b": 80},
        yaxis_title="Delta net PnL",
        xaxis_title="Scenario",
        showlegend=False,
    )
    figure.add_hline(y=0, line_width=1, line_color="#666666")
    return figure


def build_monte_carlo_percentile_figure(distributions: pa.Table) -> go.Figure:
    """Build p5 / p50 / p95 terminal-equity bars from monte_carlo_distributions."""
    figure = go.Figure()
    required = {"method", "p5_terminal_equity", "p50_terminal_equity", "p95_terminal_equity"}
    if distributions.num_rows == 0 or not required.issubset(distributions.column_names):
        figure.update_layout(
            title="Monte Carlo terminal equity percentiles",
            height=360,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
        )
        return figure

    methods = [
        _monte_carlo_method_label(distributions.column("method")[index].as_py())
        for index in range(distributions.num_rows)
    ]
    figure.add_trace(
        go.Bar(
            x=methods,
            y=[
                _numeric_metric(distributions.column("p5_terminal_equity")[index].as_py())
                for index in range(distributions.num_rows)
            ],
            name="P5 (pessimistic)",
            marker_color="#d62728",
        )
    )
    figure.add_trace(
        go.Bar(
            x=methods,
            y=[
                _numeric_metric(distributions.column("p50_terminal_equity")[index].as_py())
                for index in range(distributions.num_rows)
            ],
            name="P50 (typical)",
            marker_color="#4C78A8",
        )
    )
    figure.add_trace(
        go.Bar(
            x=methods,
            y=[
                _numeric_metric(distributions.column("p95_terminal_equity")[index].as_py())
                for index in range(distributions.num_rows)
            ],
            name="P95 (optimistic)",
            marker_color="#2ca02c",
        )
    )
    figure.update_layout(
        title="Monte Carlo terminal equity percentiles",
        barmode="group",
        height=420,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        yaxis_title="Terminal equity",
        xaxis_title="Method",
    )
    return figure


def build_monte_carlo_tail_figure(tails: pa.Table) -> go.Figure:
    """Build tail-risk probability bars from monte_carlo_tails.parquet."""
    figure = go.Figure()
    required = {
        "method",
        "probability_terminal_pnl_negative",
        "probability_max_drawdown_exceeds_threshold",
    }
    if tails.num_rows == 0 or not required.issubset(tails.column_names):
        figure.update_layout(
            title="Monte Carlo tail probabilities",
            height=360,
            margin={"l": 40, "r": 20, "t": 50, "b": 40},
        )
        return figure

    methods = [
        _monte_carlo_method_label(tails.column("method")[index].as_py())
        for index in range(tails.num_rows)
    ]
    figure.add_trace(
        go.Bar(
            x=methods,
            y=[
                _numeric_metric(tails.column("probability_terminal_pnl_negative")[index].as_py())
                for index in range(tails.num_rows)
            ],
            name="Chance of ending in loss",
            marker_color="#F58518",
        )
    )
    figure.add_trace(
        go.Bar(
            x=methods,
            y=[
                _numeric_metric(
                    tails.column("probability_max_drawdown_exceeds_threshold")[index].as_py()
                )
                for index in range(tails.num_rows)
            ],
            name="Chance of deep drawdown",
            marker_color="#E45756",
        )
    )
    figure.update_layout(
        title="Monte Carlo tail probabilities",
        barmode="group",
        height=420,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        yaxis_title="Probability",
        yaxis_tickformat=".0%",
        xaxis_title="Method",
    )
    return figure


def _stress_scenario_label(scenario_id: object) -> str:
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        return "scenario"
    known = {
        "double_commission": "Commission costs doubled",
        "remove_top_trade": "Best single trade removed",
    }
    return known.get(scenario_id, scenario_id.replace("_", " "))


def _monte_carlo_method_label(method: object) -> str:
    if not isinstance(method, str) or not method.strip():
        return "method"
    known = {
        "trade_order_shuffle": "Trade-order shuffle",
        "TRADE_ORDER_SHUFFLE": "Trade-order shuffle",
    }
    return known.get(method, method.replace("_", " "))


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
