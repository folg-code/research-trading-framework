"""Plotly figure builders for Signal Research reports."""

from __future__ import annotations

import importlib
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.reporting.signal_research.formatting import (
    format_hit_rate,
    format_return,
    format_return_short,
)


def require_plotly() -> tuple[Any, Any, Any]:
    try:
        go = importlib.import_module("plotly.graph_objects")
        pio = importlib.import_module("plotly.io")
        make_subplots = importlib.import_module("plotly.subplots").make_subplots
    except ImportError as exc:
        msg = "plotly is required for HTML reports; install with: uv pip install plotly"
        raise ValidationError(msg) from exc
    return go, pio, make_subplots


def build_horizon_mean_median_chart(
    go: Any,
    *,
    rows: list[dict[str, Any]],
) -> Any:
    labels = [
        (
            f"H={row['horizon_bars']}"
            f"<br><span style='font-size:11px;color:#64748b'>"
            f"n={row['sample_size_complete']}/{row['sample_size_total']}"
            f"</span>"
        )
        for row in rows
    ]
    means = [row["forward_return_mean"] if row["metrics_eligible"] else None for row in rows]
    medians = [row["forward_return_median"] if row["metrics_eligible"] else None for row in rows]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Mean",
            x=labels,
            y=means,
            marker_color="#2563eb",
            text=[format_return_short(value) for value in means],
            textposition="outside",
        )
    )
    figure.add_trace(
        go.Bar(
            name="Median",
            x=labels,
            y=medians,
            marker_color="#7c3aed",
            text=[format_return_short(value) for value in medians],
            textposition="outside",
        )
    )
    figure.update_layout(
        barmode="group",
        height=380,
        margin={"t": 40, "b": 40},
        yaxis_title="Return",
        yaxis_tickformat=".3%",
        legend_title_text="",
    )
    return figure


def build_metric_histogram_chart(
    go: Any,
    *,
    histogram_rows: list[dict[str, Any]],
    metric_label: str,
    metadata: AnalyticsResultMetadata,
) -> Any:
    if not histogram_rows:
        return go.Figure()

    labels = [f"{row['bin_start']:.4f}..{row['bin_end']:.4f}" for row in histogram_rows]
    counts = [int(row["count"]) for row in histogram_rows]
    reference = histogram_rows[0]
    mean_value = reference.get("reference_mean")
    median_value = reference.get("reference_median")
    shapes: list[dict[str, Any]] = []
    if mean_value is not None:
        shapes.append(
            {
                "type": "line",
                "x0": mean_value,
                "x1": mean_value,
                "y0": 0,
                "y1": 1,
                "xref": "x",
                "yref": "paper",
                "line": {"color": "#2563eb", "dash": "dash"},
            }
        )
    if median_value is not None:
        shapes.append(
            {
                "type": "line",
                "x0": median_value,
                "x1": median_value,
                "y0": 0,
                "y1": 1,
                "xref": "x",
                "yref": "paper",
                "line": {"color": "#7c3aed", "dash": "dot"},
            }
        )

    figure = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=counts,
                marker_color="#0f766e",
                hovertemplate="%{x}<br>count=%{y}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        height=360,
        margin={"t": 30, "b": 80},
        xaxis_title="Bin range",
        yaxis_title="Count",
        shapes=shapes,
        title=f"{metric_label} distribution",
    )
    if mean_value is not None or median_value is not None:
        mean_text = format_return(float(mean_value)) if mean_value is not None else "—"
        median_text = format_return(float(median_value)) if median_value is not None else "—"
        figure.add_annotation(
            text=f"Mean: {mean_text}<br>Median: {median_text}",
            xref="paper",
            yref="paper",
            x=1.0,
            y=1.12,
            showarrow=False,
            align="right",
            font={"size": 11, "color": "#475569"},
        )
    return figure


def build_grouped_stability_chart(
    go: Any,
    *,
    grouped_rows: list[dict[str, Any]],
    title: str,
) -> Any:
    labels = [
        (
            f"{row['group_value']}"
            f"<br><span style='font-size:11px;color:#64748b'>"
            f"n={row['sample_size_complete']}"
            f"</span>"
        )
        for row in grouped_rows
    ]
    means = [
        row["forward_return_mean"] if row["metrics_eligible"] else None for row in grouped_rows
    ]
    hits = [row["hit_rate"] if row["metrics_eligible"] else None for row in grouped_rows]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Mean return",
            x=labels,
            y=means,
            marker_color="#2563eb",
            yaxis="y",
        )
    )
    figure.add_trace(
        go.Scatter(
            name="Hit rate",
            x=labels,
            y=hits,
            mode="lines+markers",
            marker_color="#16a34a",
            yaxis="y2",
        )
    )
    figure.update_layout(
        title=title,
        height=360,
        margin={"t": 50, "b": 60},
        yaxis={"title": "Mean return", "tickformat": ".3%"},
        yaxis2={
            "title": "Hit rate",
            "overlaying": "y",
            "side": "right",
            "tickformat": ".0%",
        },
        legend_title_text="",
    )
    return figure


def build_baseline_chart(
    go: Any,
    make_subplots: Any,
    *,
    signal_row: dict[str, Any],
    conditional: dict[str, Any],
) -> Any:
    labels = ["Signal only", "Signal + market model"]
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Forward return mean", "Hit rate"),
        horizontal_spacing=0.1,
    )
    forward_values = [
        signal_row["forward_return_mean"],
        conditional["forward_return_mean_true"],
    ]
    hit_values = [signal_row["hit_rate"], conditional["hit_rate_true"]]
    figure.add_trace(
        go.Bar(
            x=labels,
            y=forward_values,
            text=[format_return_short(value) for value in forward_values],
            textposition="outside",
            marker_color="#2563eb",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=hit_values,
            text=[format_hit_rate(value) for value in hit_values],
            textposition="outside",
            marker_color="#16a34a",
        ),
        row=1,
        col=2,
    )
    figure.update_yaxes(title_text="Return", tickformat=".3%", row=1, col=1)
    figure.update_yaxes(title_text="Hit rate", tickformat=".0%", row=1, col=2)
    figure.update_layout(height=360, showlegend=False, margin={"t": 50, "b": 40})
    return figure
