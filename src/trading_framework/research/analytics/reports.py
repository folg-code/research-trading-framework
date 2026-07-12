"""Presentation-only HTML reports for Signal Research analytics results."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata


class AnalyticsReportSource(Protocol):
    """Minimal finished-result contract for presentation adapters."""

    @property
    def source_run_id(self) -> str: ...

    @property
    def run_summaries(self) -> pl.DataFrame: ...

    @property
    def conditional_comparison(self) -> pl.DataFrame | None: ...

    @property
    def metadata(self) -> AnalyticsResultMetadata: ...


def _require_plotly() -> tuple[Any, Any]:
    try:
        import plotly.graph_objects as go  # type: ignore[import-untyped]
        from plotly.subplots import make_subplots  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = "plotly is required for HTML reports; install with: uv pip install plotly"
        raise ValidationError(msg) from exc
    return go, make_subplots


def _metric_bar_traces(
    go: Any,
    *,
    labels: list[str],
    values: list[float | None],
    name: str,
    color: str,
) -> Any:
    numeric = [value if value is not None else 0.0 for value in values]
    return go.Bar(name=name, x=labels, y=numeric, marker_color=color)


def render_signal_research_report(
    result: AnalyticsReportSource,
    output_path: Path,
) -> Path:
    """Render an HTML dashboard from a finished analytics result.

    Presentation-only: consumes ``AnalyzeSignalResearchResult`` — no Parquet reads,
    joins or aggregate recomputation.
    """
    go, make_subplots = _require_plotly()

    run_rows = result.run_summaries.to_dicts()
    if not run_rows:
        msg = "run_summaries must contain at least one row"
        raise ValidationError(msg)

    horizon_labels = [str(row["horizon_bars"]) for row in run_rows]
    forward_returns = [row["forward_return_mean"] for row in run_rows]
    hit_rates = [row["hit_rate"] for row in run_rows]
    mfe_means = [row["mfe_mean"] for row in run_rows]
    mae_means = [row["mae_mean"] for row in run_rows]

    subplot_titles = [
        "Forward return mean by horizon",
        "Hit rate by horizon",
        "MFE mean by horizon",
        "MAE mean by horizon",
    ]
    row_count = 2
    col_count = 2

    if result.conditional_comparison is not None and len(result.conditional_comparison) > 0:
        subplot_titles.extend(["Conditional forward return", "Conditional hit rate"])
        row_count = 3
        col_count = 2

    figure = make_subplots(
        rows=row_count,
        cols=col_count,
        subplot_titles=subplot_titles,
        vertical_spacing=0.12,
    )

    figure.add_trace(
        _metric_bar_traces(
            go,
            labels=horizon_labels,
            values=forward_returns,
            name="forward_return_mean",
            color="#2563eb",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        _metric_bar_traces(
            go, labels=horizon_labels, values=hit_rates, name="hit_rate", color="#16a34a"
        ),
        row=1,
        col=2,
    )
    figure.add_trace(
        _metric_bar_traces(
            go, labels=horizon_labels, values=mfe_means, name="mfe_mean", color="#9333ea"
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        _metric_bar_traces(
            go, labels=horizon_labels, values=mae_means, name="mae_mean", color="#dc2626"
        ),
        row=2,
        col=2,
    )

    if result.conditional_comparison is not None and len(result.conditional_comparison) > 0:
        conditional = result.conditional_comparison.row(0, named=True)
        context_labels = ["context_true", "context_false"]
        figure.add_trace(
            go.Bar(
                name="forward_return_mean",
                x=context_labels,
                y=[
                    conditional["forward_return_mean_true"] or 0.0,
                    conditional["forward_return_mean_false"] or 0.0,
                ],
                marker_color="#2563eb",
            ),
            row=3,
            col=1,
        )
        figure.add_trace(
            go.Bar(
                name="hit_rate",
                x=context_labels,
                y=[conditional["hit_rate_true"] or 0.0, conditional["hit_rate_false"] or 0.0],
                marker_color="#16a34a",
            ),
            row=3,
            col=2,
        )

    scope = result.metadata.research_scope
    basis = result.metadata.timestamp_basis.value
    title = (
        f"Signal Research analytics — run {result.source_run_id} ({scope}, timestamp_basis={basis})"
    )
    figure.update_layout(
        title=title,
        barmode="group",
        height=300 * row_count,
        showlegend=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output_path), include_plotlyjs="cdn", full_html=True)
    return output_path
