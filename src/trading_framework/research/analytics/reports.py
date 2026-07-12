"""Presentation-only HTML reports for Signal Research analytics results."""

from __future__ import annotations

import html
import importlib
from pathlib import Path
from typing import Any, Protocol

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.metadata import (
    AnalyticsResultMetadata,
    describe_horizon_label,
    describe_return_semantics,
)
from trading_framework.research.scope import ResearchScope

_REPORT_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", system-ui, sans-serif;
  line-height: 1.45;
}
body {
  margin: 0;
  background: #f8fafc;
  color: #0f172a;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 2.5rem;
}
header {
  margin-bottom: 1.5rem;
}
header h1 {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}
header .meta {
  color: #475569;
  font-size: 0.95rem;
}
section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
section h2 {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
}
section p.note {
  margin: 0 0 0.75rem;
  color: #475569;
  font-size: 0.9rem;
}
table.data {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
table.data th,
table.data td {
  border: 1px solid #e2e8f0;
  padding: 0.45rem 0.55rem;
  text-align: left;
  vertical-align: top;
}
table.data th {
  background: #f1f5f9;
  font-weight: 600;
}
table.data td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
table.data tr.ineligible td {
  color: #94a3b8;
}
.chart-block {
  margin-top: 0.75rem;
}
.warning {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #9a3412;
}
.warning strong {
  display: block;
  margin-bottom: 0.25rem;
}
.caution {
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #1e3a8a;
}
"""


class AnalyticsReportSource(Protocol):
    """Minimal finished-result contract for presentation adapters."""

    @property
    def source_run_id(self) -> str: ...

    @property
    def run_summaries(self) -> pl.DataFrame: ...

    @property
    def grouped_summaries(self) -> pl.DataFrame | None: ...

    @property
    def conditional_comparison(self) -> pl.DataFrame | None: ...

    @property
    def distribution_summaries(self) -> pl.DataFrame: ...

    @property
    def join_diagnostics(self) -> pl.DataFrame: ...

    @property
    def metadata(self) -> AnalyticsResultMetadata: ...


def _require_plotly() -> tuple[Any, Any, Any]:
    try:
        go = importlib.import_module("plotly.graph_objects")
        pio = importlib.import_module("plotly.io")
        make_subplots = importlib.import_module("plotly.subplots").make_subplots
    except ImportError as exc:
        msg = "plotly is required for HTML reports; install with: uv pip install plotly"
        raise ValidationError(msg) from exc
    return go, pio, make_subplots


def _fmt_count(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}"


def _fmt_completion_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def _fmt_hit_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def _fmt_return(value: float | None) -> str:
    if value is None:
        return "—"
    bps = value * 10_000
    pct = value * 100
    return f"{bps:+.2f} bps ({pct:+.4f}%)"


def _fmt_return_short(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 10_000:+.2f} bps"


def _fmt_filter_label(metadata: AnalyticsResultMetadata) -> str:
    statuses = sorted(status.value for status in metadata.outcome_filter.aggregate_statuses)
    return ", ".join(statuses)


def _horizon_axis_labels(rows: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"H={row['horizon_bars']} bars"
            f"<br><span style='font-size:11px;color:#64748b'>"
            f"n={row['sample_size_complete']}/{row['sample_size_total']} complete"
            f"</span>"
        )
        for row in rows
    ]


def _metric_chart_values(
    rows: list[dict[str, Any]],
    metric_key: str,
    *,
    as_hit_rate: bool = False,
) -> tuple[list[float | None], list[str], list[str]]:
    values: list[float | None] = []
    bar_text: list[str] = []
    hover: list[str] = []
    for row in rows:
        eligible = bool(row["metrics_eligible"])
        minimum = int(row["minimum_required"])
        n_complete = int(row["sample_size_complete"])
        n_total = int(row["sample_size_total"])
        raw = row[metric_key]
        if not eligible:
            values.append(None)
            bar_text.append(f"n&lt;{minimum}")
            hover.append(
                f"H={row['horizon_bars']}<br>Below minimum sample ({minimum})"
                f"<br>Complete: {n_complete}/{n_total}<extra></extra>"
            )
            continue
        if raw is None:
            values.append(None)
            bar_text.append("—")
            hover.append(f"H={row['horizon_bars']}<br>No value<extra></extra>")
            continue
        numeric = float(raw)
        values.append(numeric)
        bar_text.append(_fmt_hit_rate(numeric) if as_hit_rate else _fmt_return_short(numeric))
        formatted = _fmt_hit_rate(numeric) if as_hit_rate else _fmt_return(numeric)
        hover.append(
            f"H={row['horizon_bars']}<br>{formatted}"
            f"<br>Complete: {n_complete}/{n_total}<extra></extra>"
        )
    return values, bar_text, hover


def _add_horizon_bar(
    figure: Any,
    go: Any,
    *,
    rows: list[dict[str, Any]],
    metric_key: str,
    y_title: str,
    color: str,
    row: int,
    col: int,
    as_hit_rate: bool = False,
) -> None:
    labels = _horizon_axis_labels(rows)
    values, bar_text, hover = _metric_chart_values(rows, metric_key, as_hit_rate=as_hit_rate)
    figure.add_trace(
        go.Bar(
            name=metric_key,
            x=labels,
            y=values,
            text=bar_text,
            textposition="outside",
            hovertemplate="%{hovertext}",
            hovertext=hover,
            marker_color=color,
        ),
        row=row,
        col=col,
    )
    tickformat = ".0%" if as_hit_rate else ".3%"
    figure.update_yaxes(title_text=y_title, tickformat=tickformat, row=row, col=col)
    figure.update_xaxes(title_text="Horizon (complete / total outcomes)", row=row, col=col)


def _build_horizon_charts(go: Any, make_subplots: Any, rows: list[dict[str, Any]]) -> Any:
    figure = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Forward return mean",
            "Hit rate",
            "MFE mean",
            "MAE mean",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )
    _add_horizon_bar(
        figure,
        go,
        rows=rows,
        metric_key="forward_return_mean",
        y_title="Return (%)",
        color="#2563eb",
        row=1,
        col=1,
    )
    _add_horizon_bar(
        figure,
        go,
        rows=rows,
        metric_key="hit_rate",
        y_title="Hit rate (%)",
        color="#16a34a",
        row=1,
        col=2,
        as_hit_rate=True,
    )
    _add_horizon_bar(
        figure,
        go,
        rows=rows,
        metric_key="mfe_mean",
        y_title="MFE (%)",
        color="#9333ea",
        row=2,
        col=1,
    )
    _add_horizon_bar(
        figure,
        go,
        rows=rows,
        metric_key="mae_mean",
        y_title="MAE (%)",
        color="#dc2626",
        row=2,
        col=2,
    )
    figure.update_layout(
        height=720,
        showlegend=False,
        margin={"t": 60, "b": 40},
        barmode="group",
    )
    return figure


def _build_conditional_chart(
    go: Any,
    make_subplots: Any,
    conditional: dict[str, Any],
) -> Any:
    labels = [
        (
            "Context true"
            f"<br><span style='font-size:11px;color:#64748b'>"
            f"n={conditional['context_true_sample_size']}"
            f"</span>"
        ),
        (
            "Context false"
            f"<br><span style='font-size:11px;color:#64748b'>"
            f"n={conditional['context_false_sample_size']}"
            f"</span>"
        ),
    ]
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Forward return mean", "Hit rate"),
        horizontal_spacing=0.1,
    )
    forward_values = [
        conditional["forward_return_mean_true"],
        conditional["forward_return_mean_false"],
    ]
    hit_values = [conditional["hit_rate_true"], conditional["hit_rate_false"]]
    figure.add_trace(
        go.Bar(
            x=labels,
            y=forward_values,
            text=[_fmt_return_short(value) for value in forward_values],
            textposition="outside",
            hovertemplate="%{hovertext}",
            hovertext=[_fmt_return(value) for value in forward_values],
            marker_color="#2563eb",
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=hit_values,
            text=[_fmt_hit_rate(value) for value in hit_values],
            textposition="outside",
            hovertemplate="%{hovertext}",
            hovertext=[_fmt_hit_rate(value) for value in hit_values],
            marker_color="#16a34a",
        ),
        row=1,
        col=2,
    )
    figure.update_yaxes(title_text="Return (%)", tickformat=".3%", row=1, col=1)
    figure.update_yaxes(title_text="Hit rate (%)", tickformat=".0%", row=1, col=2)
    figure.update_layout(height=380, showlegend=False, margin={"t": 50, "b": 40})
    return figure


def _sample_diagnostics_table(
    rows: list[dict[str, Any]],
    *,
    distribution_rows: dict[int, dict[str, Any]],
    metadata: AnalyticsResultMetadata,
) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th>"
        "<th>Total outcomes</th>"
        "<th>Complete</th>"
        "<th>Incomplete</th>"
        "<th>Completion rate</th>"
        "<th>Metrics computable</th>"
        "<th>Interpretation eligible</th>"
        "</tr></thead>"
    )
    body_rows: list[str] = []
    for row in rows:
        horizon = int(row["horizon_bars"])
        distribution = distribution_rows.get(horizon, {})
        computable = "Yes" if row["metrics_eligible"] else "No"
        interpretable = "Yes" if distribution.get("metrics_interpretable") else "No"
        css = "" if row["metrics_eligible"] else " class='ineligible'"
        horizon_label = describe_horizon_label(horizon_bars=horizon, metadata=metadata)
        body_rows.append(
            f"<tr{css}>"
            + "".join(
                [
                    f"<td>{html.escape(horizon_label)}</td>",
                    f"<td class='num'>{_fmt_count(int(row['sample_size_total']))}</td>",
                    f"<td class='num'>{_fmt_count(int(row['sample_size_complete']))}</td>",
                    f"<td class='num'>{_fmt_count(int(row['sample_size_incomplete']))}</td>",
                    f"<td class='num'>{_fmt_completion_rate(float(row['completion_rate']))}</td>",
                    f"<td>{computable} (n≥{metadata.min_sample_size})</td>",
                    (f"<td>{interpretable} (n≥{metadata.interpretation_min_sample_size})</td>"),
                ]
            )
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body_rows)}</tbody></table>"


def _run_metrics_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th>"
        "<th>Forward return mean</th>"
        "<th>Forward return median</th>"
        "<th>Hit rate</th>"
        "<th>MFE mean</th>"
        "<th>MAE mean</th>"
        "</tr></thead>"
    )
    body_rows: list[str] = []
    for row in rows:
        if not row["metrics_eligible"]:
            metrics = ["—", "—", "—", "—", "—"]
        else:
            metrics = [
                _fmt_return(row["forward_return_mean"]),
                _fmt_return(row["forward_return_median"]),
                _fmt_hit_rate(row["hit_rate"]),
                _fmt_return(row["mfe_mean"]),
                _fmt_return(row["mae_mean"]),
            ]
        body_rows.append(
            "<tr>"
            f"<td class='num'>{row['horizon_bars']}</td>"
            + "".join(f"<td class='num'>{value}</td>" for value in metrics)
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body_rows)}</tbody></table>"


def _grouped_summaries_table(grouped_rows: list[dict[str, Any]]) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th>"
        "<th>Dimension</th>"
        "<th>Group</th>"
        "<th>Complete</th>"
        "<th>Total</th>"
        "<th>Eligible</th>"
        "<th>Forward return mean</th>"
        "<th>Hit rate</th>"
        "<th>MFE mean</th>"
        "<th>MAE mean</th>"
        "</tr></thead>"
    )
    body_rows: list[str] = []
    for row in grouped_rows:
        eligible = "Yes" if row["metrics_eligible"] else "No"
        if not row["metrics_eligible"]:
            metric_cells = ["—", "—", "—", "—"]
        else:
            metric_cells = [
                _fmt_return(row["forward_return_mean"]),
                _fmt_hit_rate(row["hit_rate"]),
                _fmt_return(row["mfe_mean"]),
                _fmt_return(row["mae_mean"]),
            ]
        body_rows.append(
            "<tr>"
            f"<td class='num'>{row['horizon_bars']}</td>"
            f"<td>{html.escape(str(row['group_dimension']))}</td>"
            f"<td>{html.escape(str(row['group_value']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['sample_size_complete']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['sample_size_total']))}</td>"
            f"<td>{eligible}</td>"
            + "".join(f"<td class='num'>{value}</td>" for value in metric_cells)
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body_rows)}</tbody></table>"


def _conditional_table(conditional: dict[str, Any]) -> str:
    rows = [
        ("Forward return mean", "forward_return_mean"),
        ("Hit rate", "hit_rate"),
        ("MFE mean", "mfe_mean"),
        ("MAE mean", "mae_mean"),
    ]
    body: list[str] = []
    for label, prefix in rows:
        true_key = f"{prefix}_true"
        false_key = f"{prefix}_false"
        delta_key = f"{prefix}_delta"
        true_value = conditional[true_key]
        false_value = conditional[false_key]
        delta_value = conditional[delta_key]
        fmt = _fmt_hit_rate if prefix == "hit_rate" else _fmt_return
        body.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td class='num'>{fmt(true_value)}</td>"
            f"<td class='num'>{fmt(false_value)}</td>"
            f"<td class='num'>{fmt(delta_value)}</td>"
            "</tr>"
        )
    sample_row = (
        "<tr>"
        "<td>Sample size (complete outcomes)</td>"
        f"<td class='num'>{_fmt_count(int(conditional['context_true_sample_size']))}</td>"
        f"<td class='num'>{_fmt_count(int(conditional['context_false_sample_size']))}</td>"
        "<td class='num'>—</td>"
        "</tr>"
    )
    missing_row = (
        "<tr>"
        "<td>Unresolved context (excluded from both arms)</td>"
        f"<td class='num' colspan='3'>"
        f"{_fmt_count(int(conditional['context_missing_sample_size']))}</td>"
        "</tr>"
    )
    return (
        "<table class='data'>"
        "<thead><tr>"
        "<th>Metric</th><th>Context true</th><th>Context false</th>"
        "<th>Delta (true - false)</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}{sample_row}{missing_row}</tbody>"
        "</table>"
    )


def _join_diagnostics_table(
    rows: list[dict[str, Any]], *, metadata: AnalyticsResultMetadata
) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th>"
        "<th>Entities</th>"
        "<th>Outcome rows</th>"
        "<th>Complete</th>"
        "<th>Unmatched entity</th>"
        "<th>Context matched</th>"
        "<th>Context missing</th>"
        "<th>Duplicate context</th>"
        "<th>Context true</th>"
        "<th>Context false</th>"
        "<th>Context unresolved</th>"
        "<th>Overlapping windows</th>"
        "</tr></thead>"
    )
    body_rows: list[str] = []
    for row in rows:
        horizon = int(row["horizon_bars"])
        overlap = (
            f"{int(row['overlapping_outcome_windows'])} "
            f"({_fmt_completion_rate(float(row['overlapping_outcome_rate']))} of pairs)"
        )
        horizon_label = html.escape(describe_horizon_label(horizon_bars=horizon, metadata=metadata))
        body_rows.append(
            "<tr>"
            f"<td>{horizon_label}</td>"
            f"<td class='num'>{_fmt_count(int(row['entity_count']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['outcome_rows_total']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['outcome_rows_complete']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['outcome_rows_unmatched_entity']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['matched_context_rows']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['missing_context_rows']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['duplicate_context_matches']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['context_true_complete']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['context_false_complete']))}</td>"
            f"<td class='num'>{_fmt_count(int(row['context_missing_complete']))}</td>"
            f"<td class='num'>{overlap}</td>"
            "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body_rows)}</tbody></table>"


def _distribution_table(rows: list[dict[str, Any]], *, metadata: AnalyticsResultMetadata) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th>"
        "<th>Complete n</th>"
        "<th>p10</th>"
        "<th>p25</th>"
        "<th>Median</th>"
        "<th>p75</th>"
        "<th>p90</th>"
        "<th>Std dev</th>"
        "<th>Min</th>"
        "<th>Max</th>"
        "</tr></thead>"
    )
    body_rows: list[str] = []
    for row in rows:
        horizon = int(row["horizon_bars"])
        if not row["metrics_computable"]:
            cells = ["—"] * 8
        else:
            cells = [
                _fmt_return(row["forward_return_p10"]),
                _fmt_return(row["forward_return_p25"]),
                "see run summary",
                _fmt_return(row["forward_return_p75"]),
                _fmt_return(row["forward_return_p90"]),
                _fmt_return(row["forward_return_std"]),
                _fmt_return(row["forward_return_min"]),
                _fmt_return(row["forward_return_max"]),
            ]
        horizon_label = html.escape(describe_horizon_label(horizon_bars=horizon, metadata=metadata))
        body_rows.append(
            "<tr>"
            f"<td>{horizon_label}</td>"
            f"<td class='num'>{_fmt_count(int(row['sample_size_complete']))}</td>"
            + "".join(f"<td class='num'>{cell}</td>" for cell in cells)
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body_rows)}</tbody></table>"


def _conditional_warning(conditional: dict[str, Any]) -> str:
    status = str(conditional["comparison_status"])
    reason = html.escape(str(conditional["status_reason"]))
    if status == ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE.value:
        return (
            "<div class='warning'>"
            "<strong>Conditional comparison unavailable</strong>"
            f"{reason}"
            "</div>"
        )
    if status == ConditionalComparisonStatus.EMPTY_CONTROL_SAMPLE.value:
        return f"<div class='warning'><strong>Control arm unavailable</strong>{reason}</div>"
    if int(conditional["context_missing_sample_size"]) > 0:
        return f"<div class='caution'><strong>Context note</strong>{reason}</div>"
    return ""


def _overlap_warning(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    max_rate = max(float(row["overlapping_outcome_rate"]) for row in rows)
    if max_rate <= 0:
        return ""
    return (
        "<div class='caution'>"
        "<strong>Overlapping outcome windows</strong>"
        "Forward outcome windows may overlap when signals occur on nearby bars. "
        "Observations should not be interpreted as independent samples."
        "</div>"
    )


def _statistical_disclaimer() -> str:
    return (
        "<div class='caution'>"
        "<strong>Descriptive metrics only</strong>"
        "Metrics are descriptive. They do not include confidence intervals, "
        "statistical significance tests or corrections for dependent observations."
        "</div>"
    )


def _assemble_html(
    *,
    title: str,
    header_meta: str,
    methodology: str,
    overlap_warning: str,
    statistical_disclaimer: str,
    join_section: str,
    sample_table: str,
    distribution_section: str,
    metrics_section: str,
    grouped_section: str,
    conditional_section: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>{_REPORT_CSS}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{html.escape(title)}</h1>
      <div class="meta">{header_meta}</div>
    </header>
    <section id="methodology">
      <h2>How to read this report</h2>
      <p class="note">{methodology}</p>
      {statistical_disclaimer}
    </section>
    {join_section}
    <section id="sample-diagnostics">
      <h2>Sample diagnostics by horizon</h2>
      <p class="note">
        Counts are outcome rows in the analysis frame. Aggregate metrics use only rows
        with the configured outcome filter. Metrics are computable once the minimum sample
        size is reached; interpretation eligibility uses a higher threshold.
      </p>
      {overlap_warning}
      {sample_table}
    </section>
    {distribution_section}
    {metrics_section}
    {grouped_section}
    {conditional_section}
  </div>
</body>
</html>
"""


def render_signal_research_report(
    result: AnalyticsReportSource,
    output_path: Path,
) -> Path:
    """Render an HTML dashboard from a finished analytics result.

    Presentation-only: consumes ``AnalyzeSignalResearchResult`` — no Parquet reads,
    joins or aggregate recomputation.
    """
    run_rows = result.run_summaries.to_dicts()
    if not run_rows:
        msg = "run_summaries must contain at least one row"
        raise ValidationError(msg)

    go, pio, make_subplots = _require_plotly()

    metadata = result.metadata
    filter_label = _fmt_filter_label(metadata)
    scope = metadata.research_scope
    basis = metadata.timestamp_basis.value
    distribution_rows = {
        int(row["horizon_bars"]): row for row in result.distribution_summaries.to_dicts()
    }
    join_rows = result.join_diagnostics.to_dicts()

    market_models = ", ".join(metadata.market_model_ids) or "—"
    signal_models = ", ".join(metadata.signal_model_ids) or "—"
    title = f"Signal Research analytics — {result.source_run_id}"
    header_meta = (
        f"Scope: <strong>{html.escape(scope)}</strong> · "
        f"Evaluation timeframe: <strong>{html.escape(metadata.evaluation_timeframe)}</strong> · "
        f"Timestamp basis: <strong>{html.escape(basis)}</strong> · "
        f"Outcome filter: <strong>{html.escape(filter_label)}</strong><br>"
        f"Market models: <strong>{html.escape(market_models)}</strong> · "
        f"Signal models: <strong>{html.escape(signal_models)}</strong>"
    )
    scope_note = ""
    if scope == ResearchScope.MARKET_AND_SIGNAL.value:
        scope_note = (
            "Run-level metrics below are the <strong>signal baseline</strong> "
            "(all complete signal outcomes). "
            "Conditioned metrics appear only when context=true has a non-empty sample."
        )
    methodology = (
        f"{describe_return_semantics(metadata)} "
        f"{scope_note} "
        "Returns, MFE and MAE are shown in basis points (bps) and percent. "
        "Charts label each horizon with complete/total outcome counts."
    )

    horizon_figure = _build_horizon_charts(go, make_subplots, run_rows)
    horizon_chart_html = pio.to_html(horizon_figure, full_html=False, include_plotlyjs=False)
    baseline_title = (
        "Signal baseline metrics"
        if scope == ResearchScope.MARKET_AND_SIGNAL.value
        else "Run-level metrics"
    )
    metrics_section = (
        f"<section id='run-metrics'><h2>{baseline_title}</h2>"
        f"{_run_metrics_table(run_rows)}"
        f"<div class='chart-block'>{horizon_chart_html}</div></section>"
    )

    distribution_section = (
        "<section id='distribution-summaries'>"
        "<h2>Forward return distribution</h2>"
        "<p class='note'>Quantiles are computed over complete outcomes that pass the "
        "configured aggregate filter.</p>"
        f"{_distribution_table(result.distribution_summaries.to_dicts(), metadata=metadata)}"
        "</section>"
    )

    join_section = (
        "<section id='join-diagnostics'>"
        "<h2>Join diagnostics</h2>"
        "<p class='note'>Scope-aware join counts. Context states are explicit: "
        "<code>true</code>, <code>false</code> and unresolved (<code>null</code>). "
        "Unresolved context is never treated as false.</p>"
        f"{_join_diagnostics_table(join_rows, metadata=metadata)}"
        "</section>"
    )

    grouped_section = ""
    grouped = result.grouped_summaries
    if grouped is not None and len(grouped) > 0:
        grouped_rows = grouped.to_dicts()
        grouped_section = (
            "<section id='grouped-summaries'>"
            "<h2>Grouped summaries</h2>"
            "<p class='note'>Breakdown by requested group dimensions. "
            "RTH membership uses signal-time session membership at the configured "
            "timestamp basis (not the full outcome window).</p>"
            f"{_grouped_summaries_table(grouped_rows)}"
            "</section>"
        )

    conditional_section = ""
    if result.conditional_comparison is not None and len(result.conditional_comparison) > 0:
        conditional = result.conditional_comparison.row(0, named=True)
        warning = _conditional_warning(conditional)
        chart_html = ""
        if (
            int(conditional["context_true_sample_size"]) > 0
            and int(conditional["context_false_sample_size"]) > 0
        ):
            conditional_figure = _build_conditional_chart(go, make_subplots, conditional)
            chart_html = (
                f"<div class='chart-block'>"
                f"{pio.to_html(conditional_figure, full_html=False, include_plotlyjs=False)}"
                f"</div>"
            )
        conditional_section = (
            "<section id='conditional-comparison'>"
            f"<h2>Conditioned signal vs outside selected context</h2>"
            "<p class='note'>Compares complete outcomes where Market Model context was "
            "explicitly true versus explicitly false at <code>available_at</code>. "
            "This is not the same as the signal baseline above.</p>"
            f"{warning}"
            f"{_conditional_table(conditional)}"
            f"{chart_html}"
            "</section>"
        )

    document = _assemble_html(
        title=title,
        header_meta=header_meta,
        methodology=methodology,
        overlap_warning=_overlap_warning(join_rows),
        statistical_disclaimer=_statistical_disclaimer(),
        join_section=join_section,
        sample_table=_sample_diagnostics_table(
            run_rows,
            distribution_rows=distribution_rows,
            metadata=metadata,
        ),
        distribution_section=distribution_section,
        metrics_section=metrics_section,
        grouped_section=grouped_section,
        conditional_section=conditional_section,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path
