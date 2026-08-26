"""Plotly figure builders for Predictive Research diagnostic panels.

Builders consume the view model only — never raw parquet or estimators.
"""

from __future__ import annotations

import importlib
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.research.reporting.predictive.formatting import format_count, format_metric
from trading_framework.research.reporting.predictive.view_models import PredictiveReportViewModel

# Calendar order inside a fold: train, then leakage guards, then test.
_TIMELINE_ROLES = (
    FoldRole.TRAIN,
    FoldRole.PURGED,
    FoldRole.EMBARGOED,
    FoldRole.TEST,
)

_ROLE_COLORS = {
    FoldRole.TRAIN.value: "#2563eb",
    FoldRole.PURGED.value: "#f59e0b",
    FoldRole.EMBARGOED.value: "#ef4444",
    FoldRole.TEST.value: "#16a34a",
}

_BASELINE_COLORS = {
    "MODEL": "#0f172a",
    "CONSTANT_MEAN": "#94a3b8",
    "MAJORITY_CLASS": "#94a3b8",
    "RANDOM_PERMUTATION": "#f97316",
}


def require_plotly() -> tuple[Any, Any, Any]:
    try:
        go = importlib.import_module("plotly.graph_objects")
        pio = importlib.import_module("plotly.io")
        make_subplots = importlib.import_module("plotly.subplots").make_subplots
    except ImportError as exc:
        msg = "plotly is required for HTML reports; install with: uv pip install plotly"
        raise ValidationError(msg) from exc
    return go, pio, make_subplots


def build_fold_timeline_figure(go: Any, view: PredictiveReportViewModel) -> Any:
    """Horizontal bands per fold and role, with row counts on each span."""
    figure = go.Figure()
    for role in _TIMELINE_ROLES:
        bands = [band for band in view.fold_timeline if band.role == role.value]
        if not bands:
            continue
        figure.add_trace(
            go.Bar(
                name=role.value,
                y=[f"Fold {band.fold_id}" for band in bands],
                x=[max((band.end - band.start).total_seconds(), 60.0) * 1000 for band in bands],
                base=[band.start for band in bands],
                orientation="h",
                marker_color=_ROLE_COLORS[role.value],
                text=[format_count(band.row_count) for band in bands],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate=(
                    f"{role.value}<br>rows=%{{text}}<br>"
                    "start=%{base}<br>end=%{customdata}<extra></extra>"
                ),
                customdata=[band.end for band in bands],
            )
        )
    figure.update_layout(
        barmode="overlay",
        height=max(280, 90 * (len({band.fold_id for band in view.fold_timeline}) + 1)),
        xaxis_title="available_at (UTC)",
        xaxis_type="date",
        yaxis={"autorange": "reversed"},
        legend_title_text="Role",
        margin={"t": 32, "b": 40},
    )
    return figure


def build_metric_stability_figure(go: Any, view: PredictiveReportViewModel) -> Any:
    """Per-fold primary metric points with the pooled value as a reference line."""
    fold_ids = [snapshot.fold_id for snapshot in view.fold_metrics]
    values = [snapshot.model for snapshot in view.fold_metrics]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            name="Per-fold",
            x=[f"Fold {fold_id}" for fold_id in fold_ids],
            y=values,
            mode="markers+lines",
            marker={"size": 10, "color": "#2563eb"},
        )
    )
    finite = [value for value in values if value is not None]
    if len(finite) >= 2:
        spread = max(finite) - min(finite)
        figure.add_hrect(
            y0=min(finite),
            y1=max(finite),
            fillcolor="rgba(37, 99, 235, 0.08)",
            line_width=0,
            annotation_text=f"min-max spread {format_metric(spread)}",
            annotation_position="bottom left",
        )
    if view.pooled_model is not None:
        figure.add_hline(
            y=view.pooled_model,
            line_dash="dash",
            line_color="#0f172a",
            annotation_text=f"pooled {format_metric(view.pooled_model)}",
            annotation_position="top right",
        )
    figure.update_layout(
        height=360,
        yaxis_title=view.primary_metric,
        margin={"t": 32, "b": 40},
        showlegend=False,
    )
    return figure


def build_model_vs_baselines_figure(go: Any, view: PredictiveReportViewModel) -> Any:
    """Grouped bars: model and reference baselines, per fold and pooled."""
    figure = go.Figure()
    labels = [f"Fold {snapshot.fold_id}" for snapshot in view.fold_metrics] + ["Pooled"]
    model_values = [snapshot.model for snapshot in view.fold_metrics] + [view.pooled_model]
    figure.add_trace(
        go.Bar(
            name="MODEL",
            x=labels,
            y=model_values,
            marker_color=_BASELINE_COLORS["MODEL"],
            text=[format_metric(value) for value in model_values],
            textposition="outside",
        )
    )
    baseline_names = sorted(
        {name for snapshot in view.fold_metrics for name in snapshot.baselines}
        | set(view.pooled_baselines)
    )
    for name in baseline_names:
        values = [snapshot.baselines.get(name) for snapshot in view.fold_metrics]
        values.append(view.pooled_baselines.get(name))
        figure.add_trace(
            go.Bar(
                name=name,
                x=labels,
                y=values,
                marker_color=_BASELINE_COLORS.get(name, "#64748b"),
                text=[format_metric(value) for value in values],
                textposition="outside",
            )
        )
    figure.update_layout(
        barmode="group",
        height=400,
        yaxis_title=view.primary_metric,
        legend_title_text="",
        margin={"t": 40, "b": 40},
    )
    return figure


def build_sample_composition_figure(
    go: Any,
    make_subplots: Any,
    view: PredictiveReportViewModel,
) -> Any:
    """Exclusion accounting and persisted fold-role counts."""
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Build exclusions", "Fold-role rows"),
    )
    exclusion_labels = list(view.exclusion_counts)
    exclusion_values = [int(view.exclusion_counts[name]) for name in exclusion_labels]
    figure.add_trace(
        go.Bar(
            x=exclusion_labels,
            y=exclusion_values,
            marker_color="#64748b",
            text=[format_count(value) for value in exclusion_values],
            textposition="outside",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    role_labels = [role.value for role in _TIMELINE_ROLES]
    role_values = [int(view.role_counts.get(role, 0)) for role in role_labels]
    figure.add_trace(
        go.Bar(
            x=role_labels,
            y=role_values,
            marker_color=[_ROLE_COLORS[role] for role in role_labels],
            text=[format_count(value) for value in role_values],
            textposition="outside",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    figure.update_layout(height=380, margin={"t": 48, "b": 80})
    figure.update_xaxes(tickangle=-30)
    return figure
