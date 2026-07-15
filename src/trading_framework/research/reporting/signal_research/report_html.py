"""Presentation-only HTML dashboard for Signal Research report view models."""

from __future__ import annotations

import html
from pathlib import Path

import polars as pl

from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import GroupDimension
from trading_framework.research.analytics.metadata import (
    AnalyticsResultMetadata,
    describe_horizon_label,
    describe_return_semantics,
)
from trading_framework.research.reporting.signal_research.formatting import (
    format_count,
    format_filter_label,
    format_hit_rate,
    format_return,
    format_share,
)
from trading_framework.research.reporting.signal_research.plotly_figures import (
    build_baseline_chart,
    build_grouped_stability_chart,
    build_horizon_mean_median_chart,
    build_metric_histogram_chart,
    require_plotly,
)
from trading_framework.research.reporting.signal_research.view_models import (
    SignalResearchKpiCard,
    SignalResearchReportViewModel,
)
from trading_framework.research.scope import ResearchScope

_REPORT_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", system-ui, sans-serif;
  line-height: 1.45;
  --bg: #f8fafc;
  --card: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #475569;
}
body { margin: 0; background: var(--bg); color: var(--text); }
.container { max-width: 1240px; margin: 0 auto; padding: 1.5rem 1.25rem 2.5rem; }
header { margin-bottom: 1.25rem; }
header h1 { margin: 0 0 0.35rem; font-size: 1.55rem; }
header .meta { color: var(--muted); font-size: 0.92rem; }
section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
section h2 { margin: 0 0 0.75rem; font-size: 1.05rem; }
section p.note { margin: 0 0 0.75rem; color: var(--muted); font-size: 0.9rem; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
}
.kpi-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.8rem 0.9rem;
  background: #f8fafc;
}
.kpi-card .label { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.2rem; }
.kpi-card .value { font-size: 1.2rem; font-weight: 600; }
.kpi-card .sample { color: var(--muted); font-size: 0.78rem; margin-top: 0.25rem; }
table.data {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
table.data th, table.data td {
  border: 1px solid var(--border);
  padding: 0.45rem 0.55rem;
  text-align: left;
  vertical-align: top;
}
table.data th { background: #f1f5f9; font-weight: 600; }
table.data td.num { text-align: right; font-variant-numeric: tabular-nums; }
table.data tr.ineligible td { color: #94a3b8; }
.chart-block { margin-top: 0.75rem; }
.warning {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #9a3412;
}
.warning strong { display: block; margin-bottom: 0.25rem; }
.caution {
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  margin-bottom: 0.75rem;
  color: #1e3a8a;
}
"""


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(str(value))


def render_signal_research_report_html(
    view_model: SignalResearchReportViewModel,
    output_path: Path,
) -> Path:
    """Render the Wave 3 Signal Research dashboard to a single HTML file."""
    go, pio, make_subplots = require_plotly()
    metadata = view_model.metadata
    run_rows = view_model.run_summaries.to_dicts()
    primary_horizon = view_model.primary_horizon_bars

    document = _assemble_document(
        view_model=view_model,
        metadata=metadata,
        run_rows=run_rows,
        primary_horizon=primary_horizon,
        go=go,
        pio=pio,
        make_subplots=make_subplots,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _assemble_document(
    *,
    view_model: SignalResearchReportViewModel,
    metadata: AnalyticsResultMetadata,
    run_rows: list[dict[str, object]],
    primary_horizon: int,
    go: object,
    pio: object,
    make_subplots: object,
) -> str:
    title = f"Signal Research — {view_model.source_run_id}"
    sections = [
        _header_section(view_model, metadata=metadata),
        _kpi_section(view_model.kpi_cards),
        _horizon_metrics_section(view_model, run_rows=run_rows, go=go, pio=pio),
        _histogram_section(
            view_model,
            metric="forward_return",
            title="Forward return histogram",
            go=go,
            pio=pio,
            metadata=metadata,
        ),
        _histogram_section(
            view_model,
            metric="mfe",
            title="MFE distribution",
            go=go,
            pio=pio,
            metadata=metadata,
        ),
        _histogram_section(
            view_model,
            metric="mae",
            title="MAE distribution",
            go=go,
            pio=pio,
            metadata=metadata,
        ),
        _grouped_section(
            view_model,
            dimension=GroupDimension.CALENDAR_MONTH.value,
            title="Results by month",
            go=go,
            pio=pio,
            primary_horizon=primary_horizon,
        ),
        _grouped_section(
            view_model,
            dimension=GroupDimension.RTH_MEMBERSHIP.value,
            title="Results by session",
            go=go,
            pio=pio,
            primary_horizon=primary_horizon,
        ),
        _baseline_section(
            view_model,
            run_rows=run_rows,
            primary_horizon=primary_horizon,
            go=go,
            pio=pio,
            make_subplots=make_subplots,
        ),
        _diagnostics_section(view_model, metadata=metadata, run_rows=run_rows),
    ]
    body = "\n    ".join(sections)
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
    {body}
  </div>
</body>
</html>"""


def _header_section(
    view_model: SignalResearchReportViewModel,
    *,
    metadata: AnalyticsResultMetadata,
) -> str:
    market_models = ", ".join(metadata.market_model_ids) or "—"
    signal_models = ", ".join(metadata.signal_model_ids) or "—"
    dataset = html.escape(metadata.source_dataset_ref or "—")
    research_id = html.escape(metadata.research_id or "—")
    definition_hash = html.escape(metadata.definition_hash or "—")
    question = html.escape(metadata.research_question or "—")
    return (
        "<header>"
        "<h1>Signal Research Report</h1>"
        "<div class='meta'>"
        f"Run: <strong>{html.escape(view_model.source_run_id)}</strong> · "
        f"Scope: <strong>{html.escape(metadata.research_scope)}</strong> · "
        f"Generated: <strong>{view_model.generated_at_utc.isoformat()}</strong><br>"
        f"Dataset: <strong>{dataset}</strong> · "
        f"Evaluation timeframe: <strong>{html.escape(metadata.evaluation_timeframe)}</strong> · "
        f"Outcome filter: <strong>{html.escape(format_filter_label(metadata))}</strong><br>"
        f"Market models: <strong>{html.escape(market_models)}</strong> · "
        f"Signal models: <strong>{html.escape(signal_models)}</strong><br>"
        f"Research id: <strong>{research_id}</strong> · "
        f"Definition hash: <strong>{definition_hash}</strong><br>"
        f"Research question: {question}"
        "</div>"
        f"<p class='note'>{describe_return_semantics(metadata)}</p>"
        "</header>"
    )


def _kpi_section(cards: tuple[SignalResearchKpiCard, ...]) -> str:
    blocks = "".join(
        "<div class='kpi-card'>"
        f"<div class='label'>{html.escape(card.label)}</div>"
        f"<div class='value'>{html.escape(card.value)}</div>"
        f"<div class='sample'>{html.escape(card.sample_note)}</div>"
        "</div>"
        for card in cards
    )
    return (
        "<section id='kpi-cards'>"
        "<h2>Key metrics</h2>"
        f"<div class='kpi-grid'>{blocks}</div>"
        "</section>"
    )


def _horizon_metrics_section(
    view_model: SignalResearchReportViewModel,
    *,
    run_rows: list[dict[str, object]],
    go: object,
    pio: object,
) -> str:
    figure = build_horizon_mean_median_chart(go, rows=run_rows)
    chart_html = pio.to_html(figure, full_html=False, include_plotlyjs=False)  # type: ignore[attr-defined]
    table = _horizon_metrics_table(run_rows)
    return (
        "<section id='metrics-by-horizon'>"
        "<h2>Metrics by horizon</h2>"
        "<p class='note'>Every aggregate is shown with its eligible complete sample size.</p>"
        f"{table}"
        f"<div class='chart-block'>{chart_html}</div>"
        "</section>"
    )


def _horizon_metrics_table(rows: list[dict[str, object]]) -> str:
    header = (
        "<thead><tr>"
        "<th>Horizon</th><th>Sample</th><th>Mean</th><th>Median</th>"
        "<th>Hit rate</th><th>MFE</th><th>MAE</th>"
        "</tr></thead>"
    )
    body: list[str] = []
    for row in rows:
        if not row["metrics_eligible"]:
            metrics = ["—", "—", "—", "—", "—"]
        else:
            metrics = [
                format_return(float(row["forward_return_mean"])),  # type: ignore[arg-type]
                format_return(float(row["forward_return_median"])),  # type: ignore[arg-type]
                format_hit_rate(float(row["hit_rate"])),  # type: ignore[arg-type]
                format_return(float(row["mfe_mean"])),  # type: ignore[arg-type]
                format_return(float(row["mae_mean"])),  # type: ignore[arg-type]
            ]
        body.append(
            "<tr>"
            f"<td class='num'>{row['horizon_bars']}</td>"
            f"<td class='num'>{format_count(int(str(row['sample_size_complete'])))}</td>"
            + "".join(f"<td class='num'>{value}</td>" for value in metrics)
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body)}</tbody></table>"


def _histogram_section(
    view_model: SignalResearchReportViewModel,
    *,
    metric: str,
    title: str,
    go: object,
    pio: object,
    metadata: AnalyticsResultMetadata,
) -> str:
    rows = (
        view_model.metric_histograms.filter(
            (pl.col("horizon_bars") == view_model.primary_horizon_bars)
            & (pl.col("metric") == metric)
        )
        .sort("bin_index")
        .to_dicts()
    )
    horizon_label = describe_horizon_label(
        horizon_bars=view_model.primary_horizon_bars,
        metadata=metadata,
    )
    figure = build_metric_histogram_chart(
        go,
        histogram_rows=rows,
        metric_label=metric.replace("_", " ").title(),
        metadata=metadata,
    )
    chart_html = pio.to_html(figure, full_html=False, include_plotlyjs=False)  # type: ignore[attr-defined]
    return (
        f"<section id='histogram-{metric}'>"
        f"<h2>{html.escape(title)}</h2>"
        f"<p class='note'>Primary horizon: {html.escape(horizon_label)}. "
        "Dashed line = mean, dotted line = median, zero reference implicit at bin scale.</p>"
        f"<div class='chart-block'>{chart_html}</div>"
        "</section>"
    )


def _grouped_section(
    view_model: SignalResearchReportViewModel,
    *,
    dimension: str,
    title: str,
    go: object,
    pio: object,
    primary_horizon: int,
) -> str:
    grouped = view_model.grouped_summaries
    if grouped is None or grouped.height == 0:
        return (
            f"<section id='grouped-{dimension}'><h2>{html.escape(title)}</h2>"
            "<p class='note'>No grouped analytics were requested for this run.</p></section>"
        )
    rows = grouped.filter(
        (pl.col("horizon_bars") == primary_horizon) & (pl.col("group_dimension") == dimension)
    ).to_dicts()
    if not rows:
        return (
            f"<section id='grouped-{dimension}'><h2>{html.escape(title)}</h2>"
            "<p class='note'>No grouped rows for the primary horizon.</p></section>"
        )
    table = _grouped_table(rows)
    figure = build_grouped_stability_chart(go, grouped_rows=rows, title=title)
    chart_html = pio.to_html(figure, full_html=False, include_plotlyjs=False)  # type: ignore[attr-defined]
    return (
        f"<section id='grouped-{dimension}'>"
        f"<h2>{html.escape(title)}</h2>"
        f"{table}<div class='chart-block'>{chart_html}</div>"
        "</section>"
    )


def _grouped_table(rows: list[dict[str, object]]) -> str:
    header = (
        "<thead><tr>"
        "<th>Group</th><th>Sample</th><th>Mean</th><th>Median</th><th>Hit rate</th>"
        "</tr></thead>"
    )
    body: list[str] = []
    for row in rows:
        if not row["metrics_eligible"]:
            cells = ["—", "—", "—"]
        else:
            cells = [
                format_return(float(row["forward_return_mean"])),  # type: ignore[arg-type]
                format_return(float(row["forward_return_median"])),  # type: ignore[arg-type]
                format_hit_rate(float(row["hit_rate"])),  # type: ignore[arg-type]
            ]
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row['group_value']))}</td>"
            f"<td class='num'>{format_count(int(str(row['sample_size_complete'])))}</td>"
            + "".join(f"<td class='num'>{cell}</td>" for cell in cells)
            + "</tr>"
        )
    return f"<table class='data'>{header}<tbody>{''.join(body)}</tbody></table>"


def _baseline_section(
    view_model: SignalResearchReportViewModel,
    *,
    run_rows: list[dict[str, object]],
    primary_horizon: int,
    go: object,
    pio: object,
    make_subplots: object,
) -> str:
    scope = ResearchScope(view_model.metadata.research_scope)
    signal_row = next(row for row in run_rows if int(str(row["horizon_bars"])) == primary_horizon)
    if scope is not ResearchScope.MARKET_AND_SIGNAL:
        return (
            "<section id='baseline-comparison'><h2>Baseline comparison</h2>"
            "<p class='note'>Baseline comparison applies to MARKET_AND_SIGNAL scope only. "
            "Run-level metrics above describe this study.</p></section>"
        )
    conditional_df = view_model.conditional_comparison
    if conditional_df is None or conditional_df.height == 0:
        return (
            "<section id='baseline-comparison'><h2>Baseline comparison</h2>"
            "<p class='note'>Conditional comparison was not computed for this run.</p></section>"
        )
    conditional = conditional_df.filter(pl.col("horizon_bars") == primary_horizon).row(
        0, named=True
    )
    warning = ""
    if str(conditional["comparison_status"]) == (
        ConditionalComparisonStatus.EMPTY_CONDITIONED_SAMPLE.value
    ):
        warning = (
            "<div class='warning'><strong>Conditioned sample empty</strong>"
            f"{html.escape(str(conditional['status_reason']))}</div>"
        )
    table = _baseline_table(signal_row=signal_row, conditional=conditional)
    chart_html = ""
    if int(str(conditional["context_true_sample_size"])) > 0 and signal_row["metrics_eligible"]:
        figure = build_baseline_chart(
            go,
            make_subplots,
            signal_row=signal_row,
            conditional=conditional,
        )
        chart_html = (
            "<div class='chart-block'>"
            f"{pio.to_html(figure, full_html=False, include_plotlyjs=False)}"  # type: ignore[attr-defined]
            "</div>"
        )
    return (
        "<section id='baseline-comparison'>"
        "<h2>Signal-only vs conditioned signal</h2>"
        "<p class='note'>Marginal contribution compares the full signal sample with outcomes "
        "where market-model context was explicitly true.</p>"
        f"{warning}{table}{chart_html}"
        "</section>"
    )


def _baseline_table(
    *,
    signal_row: dict[str, object],
    conditional: dict[str, object],
) -> str:
    def row_cells(
        label: str,
        sample: int | None,
        mean: object,
        median: object,
        hit: object,
        mfe: object,
        mae: object,
        *,
        hit_rate_only: bool = False,
    ) -> str:
        if hit_rate_only:
            mean_value = _optional_float(mean)
            median_value = _optional_float(median)
            mean_cell = format_hit_rate(mean_value) if mean_value is not None else "—"
            median_cell = format_hit_rate(median_value) if median_value is not None else "—"
        else:
            mean_value = _optional_float(mean)
            median_value = _optional_float(median)
            mean_cell = format_return(mean_value) if mean_value is not None else "—"
            median_cell = format_return(median_value) if median_value is not None else "—"
        hit_value = _optional_float(hit)
        mfe_value = _optional_float(mfe)
        mae_value = _optional_float(mae)
        return (
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td class='num'>{format_count(sample)}</td>"
            f"<td class='num'>{mean_cell}</td>"
            f"<td class='num'>{median_cell}</td>"
            f"<td class='num'>{format_hit_rate(hit_value) if hit_value is not None else '—'}</td>"
            f"<td class='num'>{format_return(mfe_value) if mfe_value is not None else '—'}</td>"
            f"<td class='num'>{format_return(mae_value) if mae_value is not None else '—'}</td>"
            "</tr>"
        )

    rows = [
        row_cells(
            "Signal only",
            int(str(signal_row["sample_size_complete"])),
            signal_row["forward_return_mean"],
            signal_row["forward_return_median"],
            signal_row["hit_rate"],
            signal_row["mfe_mean"],
            signal_row["mae_mean"],
        ),
        row_cells(
            "Signal + market model",
            int(str(conditional["context_true_sample_size"])),
            conditional["forward_return_mean_true"],
            conditional["forward_return_median_true"],
            conditional["hit_rate_true"],
            conditional["mfe_mean_true"],
            conditional["mae_mean_true"],
        ),
        row_cells(
            "Marginal contribution",
            None,
            conditional["forward_return_mean_delta"],
            conditional["forward_return_median_delta"],
            conditional["hit_rate_delta"],
            conditional["mfe_mean_delta"],
            conditional["mae_mean_delta"],
        ),
    ]
    return (
        "<table class='data'><thead><tr>"
        "<th>Variant</th><th>Sample</th><th>Mean</th><th>Median</th>"
        "<th>Hit rate</th><th>MFE</th><th>MAE</th>"
        "</tr></thead><tbody>"
        f"{''.join(rows)}"
        "</tbody></table>"
    )


def _diagnostics_section(
    view_model: SignalResearchReportViewModel,
    *,
    metadata: AnalyticsResultMetadata,
    run_rows: list[dict[str, object]],
) -> str:
    join_rows = view_model.join_diagnostics.to_dicts()
    quality_blocks = (
        "".join(
            "<div class='warning'>"
            f"<strong>{html.escape(warning.code.value)}</strong>"
            f"{html.escape(warning.message)}"
            "</div>"
            for warning in view_model.quality_warnings
        )
        or "<p class='note'>No quality diagnostic flags triggered.</p>"
    )
    sample_rows = "".join(_sample_completeness_row(row, metadata=metadata) for row in run_rows)
    return (
        "<section id='diagnostics'><h2>Diagnostics</h2>"
        "<h3>Quality flags</h3>"
        f"{quality_blocks}"
        "<h3>Sample completeness</h3>"
        "<table class='data'><thead><tr>"
        "<th>Horizon</th><th>Total</th><th>Complete</th><th>Incomplete</th><th>Completion</th>"
        "</tr></thead>"
        f"<tbody>{sample_rows}</tbody></table>"
        "<h3>Join diagnostics</h3>"
        f"{_join_table(join_rows, metadata=metadata)}"
        "</section>"
    )


def _sample_completeness_row(
    row: dict[str, object],
    *,
    metadata: AnalyticsResultMetadata,
) -> str:
    horizon_label = describe_horizon_label(
        horizon_bars=int(str(row["horizon_bars"])),
        metadata=metadata,
    )
    return (
        "<tr>"
        f"<td>{html.escape(horizon_label)}</td>"
        f"<td class='num'>{format_count(int(str(row['sample_size_total'])))}</td>"
        f"<td class='num'>{format_count(int(str(row['sample_size_complete'])))}</td>"
        f"<td class='num'>{format_count(int(str(row['sample_size_incomplete'])))}</td>"
        f"<td class='num'>{format_share(float(str(row['completion_rate'])))}</td>"
        "</tr>"
    )


def _join_table(
    rows: list[dict[str, object]],
    *,
    metadata: AnalyticsResultMetadata,
) -> str:
    body: list[str] = []
    for row in rows:
        horizon = describe_horizon_label(
            horizon_bars=int(str(row["horizon_bars"])),
            metadata=metadata,
        )
        body.append(
            "<tr>"
            f"<td>{html.escape(horizon)}</td>"
            f"<td class='num'>{format_count(int(str(row['outcome_rows_complete'])))}</td>"
            f"<td class='num'>{format_count(int(str(row['context_true_complete'])))}</td>"
            f"<td class='num'>{format_count(int(str(row['context_false_complete'])))}</td>"
            f"<td class='num'>{format_count(int(str(row['context_missing_complete'])))}</td>"
            f"<td class='num'>{format_count(int(str(row['overlapping_outcome_windows'])))}</td>"
            "</tr>"
        )
    return (
        "<table class='data'><thead><tr>"
        "<th>Horizon</th><th>Complete</th><th>Context true</th><th>Context false</th>"
        "<th>Unresolved</th><th>Overlapping windows</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )
