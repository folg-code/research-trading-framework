"""Plotly figure builders for Predictive Research report panels.

Builders consume the view model only — never raw parquet or estimators.
"""

from __future__ import annotations

import importlib
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.research.reporting.predictive.display_series import (
    brier_decomposition,
    build_pr_curves,
    build_prediction_buckets,
    build_residual_histogram,
    build_roc_curves,
    build_scatter_series,
    calibration_bins_from_predictions,
    reliability_points,
)
from trading_framework.research.reporting.predictive.formatting import (
    format_count,
    format_metric,
    format_return,
)
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

_FOLD_COLORS = ("#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8")
_POOLED_COLOR = "#0f172a"


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


def build_prediction_quality_figure(
    go: Any,
    make_subplots: Any,
    view: PredictiveReportViewModel,
) -> Any:
    """Regression scatter, per-fold rank IC, and residual distribution."""
    scatter = build_scatter_series(view.predictions)
    residuals = build_residual_histogram(view.predictions)
    figure = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("Predicted vs realized", "Rank IC by fold", "Residuals"),
    )
    figure.add_trace(
        go.Scatter(
            name="OOS rows",
            x=scatter.predicted.tolist(),
            y=scatter.realized.tolist(),
            mode="markers",
            marker={"size": 7, "color": "#2563eb", "opacity": 0.65},
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    if scatter.slope is not None and scatter.intercept is not None and scatter.predicted.size:
        x_line = [float(scatter.predicted.min()), float(scatter.predicted.max())]
        y_line = [scatter.slope * x_value + scatter.intercept for x_value in x_line]
        figure.add_trace(
            go.Scatter(
                name="Fitted line",
                x=x_line,
                y=y_line,
                mode="lines",
                line={"color": "#0f172a", "dash": "dash"},
                showlegend=False,
            ),
            row=1,
            col=1,
        )
    figure.add_trace(
        go.Bar(
            name="Rank IC",
            x=[f"Fold {snapshot.fold_id}" for snapshot in view.fold_metrics],
            y=[snapshot.model for snapshot in view.fold_metrics],
            marker_color="#2563eb",
            text=[format_metric(snapshot.model) for snapshot in view.fold_metrics],
            textposition="outside",
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    figure.add_trace(
        go.Bar(
            name="Residuals",
            x=residuals.centers.tolist(),
            y=residuals.counts.tolist(),
            marker_color="#64748b",
            showlegend=False,
        ),
        row=1,
        col=3,
    )
    figure.update_xaxes(title_text="y_pred", row=1, col=1)
    figure.update_yaxes(title_text="y_true", row=1, col=1)
    figure.update_yaxes(title_text=view.primary_metric, row=1, col=2)
    figure.update_layout(height=400, margin={"t": 48, "b": 48})
    return figure


def build_discrimination_figure(
    go: Any,
    make_subplots: Any,
    view: PredictiveReportViewModel,
) -> Any:
    """Per-fold ROC and precision-recall, with the pooled curve emphasized."""
    figure = make_subplots(rows=1, cols=2, subplot_titles=("ROC", "Precision-Recall"))
    roc_series = build_roc_curves(view.predictions)
    pr_series = build_pr_curves(view.predictions)
    _add_curve_traces(go, figure, roc_series, row=1, col=1, x_name="FPR", y_name="TPR")
    _add_curve_traces(go, figure, pr_series, row=1, col=2, x_name="Recall", y_name="Precision")
    figure.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"color": "#cbd5e1", "dash": "dot"},
            name="Chance",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    figure.update_layout(height=420, margin={"t": 48, "b": 48}, legend_title_text="")
    return figure


def build_calibration_figure(
    go: Any,
    make_subplots: Any,
    view: PredictiveReportViewModel,
) -> Any:
    """Reliability curve from persisted bins, with Brier decomposition."""
    bins = view.calibration_bins or calibration_bins_from_predictions(view.predictions)
    points = reliability_points(bins)
    decomposition = brier_decomposition(bins, persisted_brier=view.brier_score)
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Reliability", "Brier decomposition"),
    )
    figure.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"color": "#cbd5e1", "dash": "dot"},
            name="Perfect",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            name="Occupied bins",
            x=[point.mean_predicted for point in points],
            y=[point.mean_observed for point in points],
            mode="markers+lines",
            marker={"size": 10, "color": "#2563eb"},
            text=[format_count(point.count) for point in points],
            hovertemplate="predicted=%{x:.3f}<br>observed=%{y:.3f}<br>n=%{text}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    if decomposition is not None:
        labels = ["Reliability", "Resolution", "Uncertainty"]
        values = [
            decomposition.reliability,
            decomposition.resolution,
            decomposition.uncertainty,
        ]
        if decomposition.persisted_brier is not None:
            labels.append("Brier")
            values.append(decomposition.persisted_brier)
        figure.add_trace(
            go.Bar(
                x=labels,
                y=values,
                marker_color=["#f97316", "#16a34a", "#64748b", "#0f172a"][: len(values)],
                text=[format_metric(value) for value in values],
                textposition="outside",
                showlegend=False,
            ),
            row=1,
            col=2,
        )
    figure.update_xaxes(title_text="Mean predicted", range=[-0.05, 1.05], row=1, col=1)
    figure.update_yaxes(title_text="Mean observed", range=[-0.05, 1.05], row=1, col=1)
    figure.update_layout(height=400, margin={"t": 48, "b": 48})
    return figure


def build_prediction_buckets_figure(go: Any, view: PredictiveReportViewModel) -> Any:
    """Mean forward return per prediction decile, out-of-sample only."""
    buckets = build_prediction_buckets(view.predictions)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Decile mean",
            x=[f"D{bucket.decile}" for bucket in buckets],
            y=[bucket.mean_forward_return for bucket in buckets],
            marker_color="#2563eb",
            text=[
                f"{format_return(bucket.mean_forward_return)} n={bucket.count}"
                for bucket in buckets
            ],
            textposition="outside",
        )
    )
    if view.mean_forward_return_all is not None:
        figure.add_hline(
            y=view.mean_forward_return_all,
            line_dash="dash",
            line_color="#0f172a",
            annotation_text=f"all-rows {format_return(view.mean_forward_return_all)}",
            annotation_position="top right",
        )
    figure.update_layout(
        height=400,
        yaxis_title="mean forward_return",
        margin={"t": 40, "b": 40},
        showlegend=False,
    )
    return figure


def _add_curve_traces(
    go: Any,
    figure: Any,
    series: tuple[Any, ...],
    *,
    row: int,
    col: int,
    x_name: str,
    y_name: str,
) -> None:
    for index, curve in enumerate(series):
        is_pooled = curve.fold_id is None
        color = _POOLED_COLOR if is_pooled else _FOLD_COLORS[index % len(_FOLD_COLORS)]
        figure.add_trace(
            go.Scatter(
                name="Pooled" if is_pooled else f"Fold {curve.fold_id}",
                x=curve.x.tolist(),
                y=curve.y.tolist(),
                mode="lines",
                line={"color": color, "width": 3 if is_pooled else 1.5},
                legendgroup=str(curve.fold_id) if curve.fold_id is not None else "pooled",
                showlegend=col == 1,
            ),
            row=row,
            col=col,
        )
    figure.update_xaxes(title_text=x_name, range=[-0.02, 1.02], row=row, col=col)
    figure.update_yaxes(title_text=y_name, range=[-0.02, 1.02], row=row, col=col)
