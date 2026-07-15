"""Presentation-only HTML dashboard for Robustness Research report view models."""

from __future__ import annotations

import html
import json
from decimal import Decimal
from pathlib import Path

from trading_framework.research.robustness.analytics.parameter_sweep import ParameterHeatmapView
from trading_framework.research.robustness.report import RobustnessReportViewModel
from trading_framework.research.robustness.report_formatting import (
    build_config_label_lookup,
    format_axis_name,
    format_axis_value,
    format_config_label,
    format_dataset_label,
    format_fold_label,
    format_gate_label,
    format_gate_message,
    format_kind_label,
    format_metric_label,
    format_money,
    format_parameter_settings,
    format_probability,
    format_scenario_label,
    format_share,
    format_significant,
    format_strategy_template,
    format_strength_or_weakness,
    format_verdict_badge,
    format_verdict_headline,
    format_verdict_summary,
)
from trading_framework.research.robustness.verdict import VerdictKind

_LIGHTWEIGHT_CHARTS_CDN = (
    "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"
)

_REPORT_CSS = """
:root {
  color-scheme: light;
  font-family: "Segoe UI", system-ui, sans-serif;
  line-height: 1.5;
  --bg: #f8fafc;
  --card: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #475569;
  --positive: #15803d;
  --negative: #b91c1c;
  --accent: #1d4ed8;
  --pass: #166534;
  --pass-bg: #dcfce7;
  --conditional: #92400e;
  --conditional-bg: #fef3c7;
  --fail: #991b1b;
  --fail-bg: #fee2e2;
}
body { margin: 0; background: var(--bg); color: var(--text); }
.container { max-width: 1400px; margin: 0 auto; padding: 1.5rem 1.25rem 2.5rem; }
header { margin-bottom: 1.25rem; }
header h1 { margin: 0 0 0.35rem; font-size: 1.55rem; }
header .meta { color: var(--muted); font-size: 0.92rem; }
header .lead { margin: 0.75rem 0 0; max-width: 72ch; color: var(--text); font-size: 0.98rem; }
.verdict-hero {
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
  margin-bottom: 1rem;
  border: 1px solid var(--border);
}
.verdict-hero.pass { background: var(--pass-bg); border-color: #86efac; }
.verdict-hero.conditional { background: var(--conditional-bg); border-color: #fcd34d; }
.verdict-hero.fail { background: var(--fail-bg); border-color: #fca5a5; }
.verdict-badge {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  margin-bottom: 0.55rem;
}
.verdict-badge.pass { background: #15803d; color: #fff; }
.verdict-badge.conditional { background: #b45309; color: #fff; }
.verdict-badge.fail { background: #b91c1c; color: #fff; }
.verdict-headline { font-size: 1.15rem; font-weight: 600; margin: 0 0 0.45rem; }
.verdict-summary { font-size: 0.96rem; margin: 0 0 0.75rem; color: var(--text); }
.bullet-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}
.bullet-card {
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 8px;
  padding: 0.75rem 0.85rem;
}
.bullet-card h3 { margin: 0 0 0.45rem; font-size: 0.88rem; color: var(--muted); }
.bullet-card ul { margin: 0; padding-left: 1.1rem; font-size: 0.86rem; }
section.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
section.panel h2 { margin: 0 0 0.45rem; font-size: 1.05rem; }
section.panel h3 { margin: 1rem 0 0.45rem; font-size: 0.95rem; color: var(--muted); }
.section-intro {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 0.85rem;
  max-width: 78ch;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.kpi-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.7rem 0.8rem;
  background: #fcfdff;
}
.kpi-card .label {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.kpi-card .value {
  margin-top: 0.2rem;
  font-size: 1.15rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.kpi-card .value.positive { color: var(--positive); }
.kpi-card .value.negative { color: var(--negative); }
.chart-box {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  margin-bottom: 0.85rem;
}
.chart-box .chart-title {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.86rem;
  color: var(--muted);
}
.chart-host { width: 100%; height: 320px; }
table.data {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.86rem;
}
table.data th, table.data td {
  border: 1px solid var(--border);
  padding: 0.42rem 0.5rem;
  text-align: left;
}
table.data th { background: #f1f5f9; }
table.data td.num { text-align: right; font-variant-numeric: tabular-nums; }
.heatmap {
  display: grid;
  gap: 2px;
  width: fit-content;
  max-width: 100%;
}
.heatmap-cell {
  min-width: 64px;
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
  border-radius: 4px;
  border: 1px solid rgba(0,0,0,0.05);
}
.heatmap-axis {
  font-size: 0.75rem;
  color: var(--muted);
  text-align: center;
}
.note { color: var(--muted); font-size: 0.88rem; margin: 0 0 0.75rem; }
.nav-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-bottom: 1rem;
}
.nav-pills a {
  text-decoration: none;
  color: var(--accent);
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 0.3rem 0.7rem;
  font-size: 0.82rem;
}
details.technical {
  margin-top: 0.75rem;
  font-size: 0.82rem;
  color: var(--muted);
}
details.technical summary { cursor: pointer; }
"""


def render_robustness_report(
    view_model: RobustnessReportViewModel,
    output_path: Path,
) -> Path:
    """Render a standalone Robustness Research dashboard HTML file."""
    payload_json = json.dumps(view_model.to_dict(), indent=2)
    config_lookup = build_config_label_lookup(view_model)
    title = "Strategy Robustness Report"
    tests_run = ", ".join(format_kind_label(kind) for kind in view_model.kinds)
    strategy_label = html.escape(format_strategy_template(view_model.strategy_template_id))
    header_meta = (
        f"<strong>Strategy:</strong> {strategy_label}"
        f"<br><strong>Data:</strong> {html.escape(format_dataset_label(view_model.dataset_ref))}"
        f"<br><strong>Tests included:</strong> {html.escape(tests_run)}"
    )
    document = _render_document(
        title=title,
        header_meta=header_meta,
        view_model=view_model,
        payload_json=payload_json,
        config_lookup=config_lookup,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _render_document(
    *,
    title: str,
    header_meta: str,
    view_model: RobustnessReportViewModel,
    payload_json: str,
    config_lookup: dict[str, dict[str, str]],
) -> str:
    sections = _section_nav(view_model)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script src="{_LIGHTWEIGHT_CHARTS_CDN}"></script>
  <style>{_REPORT_CSS}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{html.escape(title)}</h1>
      <div class="meta">{header_meta}</div>
      <p class="lead">
        This report checks whether a trading strategy still looks reasonable when we change
        its settings, test on unseen time periods, apply tougher assumptions, and shuffle trade
        order. A good grid ranking alone does not mean the strategy is safe to use.
      </p>
    </header>
    {_verdict_hero(view_model, config_lookup)}
    <nav class="nav-pills">{sections}</nav>
    {_overview_section(view_model, config_lookup)}
    {_parameter_section(view_model, config_lookup)}
    {_walk_forward_section(view_model, config_lookup)}
    {_stress_section(view_model)}
    {_monte_carlo_section(view_model)}
    {_diagnostics_section(view_model)}
    {_assumptions_section(view_model)}
  </div>
  <script id="report-data" type="application/json">{payload_json}</script>
  <script>{_report_js()}</script>
</body>
</html>
"""


def _section_intro(text: str) -> str:
    return f'<p class="section-intro">{html.escape(text)}</p>'


def _verdict_class(verdict: VerdictKind) -> str:
    if verdict is VerdictKind.PASS:
        return "pass"
    if verdict is VerdictKind.CONDITIONAL:
        return "conditional"
    return "fail"


def _verdict_hero(
    view_model: RobustnessReportViewModel,
    config_lookup: dict[str, dict[str, str]],
) -> str:
    verdict = view_model.verdict
    badge_class = _verdict_class(verdict.verdict)
    strengths = (
        "".join(
            f"<li>{html.escape(format_strength_or_weakness(item))}</li>"
            for item in verdict.strengths
        )
        or "<li>No standout strengths recorded.</li>"
    )
    weaknesses = (
        "".join(f"<li>{html.escape(item)}</li>" for item in verdict.weaknesses)
        or "<li>No softer concerns recorded.</li>"
    )
    blocking = (
        "".join(f"<li>{html.escape(item)}</li>" for item in verdict.blocking_issues)
        or "<li>No blocking issues.</li>"
    )
    best_rank = ""
    if verdict.best_ranked_config_id is not None:
        best_label = format_config_label(verdict.best_ranked_config_id, lookup=config_lookup)
        best_rank = (
            "<p class='note'>Best-performing settings in the parameter grid "
            f"(ranking only, not validation): <strong>{html.escape(best_label)}</strong></p>"
        )
    summary = format_verdict_summary(verdict.summary, lookup=config_lookup)
    return f"""
    <section class="verdict-hero {badge_class}" id="verdict">
      <div class="verdict-badge {badge_class}">
        {html.escape(format_verdict_badge(verdict.verdict))}
      </div>
      <p class="verdict-headline">{html.escape(format_verdict_headline(verdict.verdict))}</p>
      <p class="verdict-summary">{html.escape(summary)}</p>
      {best_rank}
      <div class="bullet-grid">
        <div class="bullet-card"><h3>What looks good</h3><ul>{strengths}</ul></div>
        <div class="bullet-card"><h3>What to watch</h3><ul>{weaknesses}</ul></div>
        <div class="bullet-card"><h3>Blocking problems</h3><ul>{blocking}</ul></div>
      </div>
    </section>
    """


def _section_nav(view_model: RobustnessReportViewModel) -> str:
    links = [
        '<a href="#verdict">Overall verdict</a>',
        '<a href="#overview">At a glance</a>',
    ]
    if view_model.parameter_sweep is not None:
        links.append('<a href="#parameter">Parameter comparison</a>')
    if view_model.walk_forward is not None:
        links.append('<a href="#walk-forward">Walk-forward</a>')
    if view_model.stress is not None:
        links.append('<a href="#stress">Stress tests</a>')
    if view_model.monte_carlo is not None:
        links.append('<a href="#monte-carlo">Monte Carlo</a>')
    if view_model.diagnostics is not None:
        links.append('<a href="#diagnostics">Health checks</a>')
    links.append('<a href="#assumptions">Rules &amp; checklist</a>')
    return "".join(links)


def _overview_section(
    view_model: RobustnessReportViewModel,
    config_lookup: dict[str, dict[str, str]],
) -> str:
    kpis: list[str] = []
    if view_model.parameter_sweep and view_model.parameter_sweep.rankings:
        best = view_model.parameter_sweep.rankings[0]
        kpis.append(_kpi("Best grid profit", format_money(best.net_pnl), best.net_pnl >= 0))
        kpis.append(_kpi("Trades (best grid)", str(best.trade_count), None))
    if view_model.walk_forward is not None:
        oos_net = sum(
            evaluation.oos_summary.net_pnl
            for evaluation in view_model.walk_forward.fold_evaluations
        )
        kpis.append(_kpi("Walk-forward profit", format_money(oos_net), oos_net >= 0))
        kpis.append(
            _kpi(
                "Walk-forward periods",
                str(len(view_model.walk_forward.fold_evaluations)),
                None,
            )
        )
    if view_model.stress is not None:
        kpis.append(_kpi("Stress scenarios run", str(len(view_model.stress.rows)), None))
    if view_model.monte_carlo is not None and view_model.monte_carlo.distribution_summaries:
        summary = view_model.monte_carlo.distribution_summaries[0]
        kpis.append(
            _kpi(
                "Typical ending equity (MC)",
                format_money(summary.p50_terminal_equity),
                None,
            )
        )
    if view_model.diagnostics is not None:
        conc = abs(view_model.diagnostics.pnl_concentration.top_trades_share)
        kpis.append(
            _kpi(
                "Profit from top trades",
                format_share(conc),
                conc <= Decimal("0.5"),
            )
        )
    if not kpis:
        kpis.append(_kpi("Tests run", str(len(view_model.kinds)), None))
    return f"""
    <section class="panel" id="overview">
      <h2>At a glance</h2>
      {
        _section_intro(
            "A short summary of the headline numbers. Use the sections below for context "
            "on what each test means and why it matters."
        )
    }
      <div class="kpi-grid">{"".join(kpis)}</div>
    </section>
    """


def _format_optional_money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return format_money(value)


def _kpi(label: str, value: str, positive: bool | None) -> str:
    value_class = ""
    if positive is True:
        value_class = " positive"
    elif positive is False:
        value_class = " negative"
    return (
        f"<div class='kpi-card'><div class='label'>{html.escape(label)}</div>"
        f"<div class='value{value_class}'>{html.escape(value)}</div></div>"
    )


def _parameter_section(
    view_model: RobustnessReportViewModel,
    config_lookup: dict[str, dict[str, str]],
) -> str:
    sweep = view_model.parameter_sweep
    if sweep is None:
        return ""
    ranking_rows = "".join(
        (
            "<tr>"
            f"<td>{row.rank}</td>"
            f"<td>{html.escape(format_parameter_settings(row.parameter_overrides))}</td>"
            f"<td class='num'>{html.escape(format_money(row.net_pnl))}</td>"
            f"<td class='num'>{html.escape(format_money(row.max_drawdown))}</td>"
            f"<td class='num'>{row.trade_count}</td>"
            "</tr>"
        )
        for row in sweep.rankings[:10]
    )
    heatmaps = "".join(_heatmap_html(heatmap) for heatmap in sweep.heatmaps[:2])
    isolated = "".join(
        (
            "<tr>"
            f"<td>{html.escape(format_config_label(flag.config_id, lookup=config_lookup))}</td>"
            f"<td class='num'>{html.escape(format_money(flag.net_pnl))}</td>"
            f"<td>{html.escape(_isolated_reason(flag.reason))}</td>"
            "</tr>"
        )
        for flag in sweep.isolated_optima
        if flag.is_isolated_optimum
    )
    isolated_table = (
        (
            "<h3>Settings that look like lucky one-offs</h3>"
            "<p class='note'>"
            "These combinations score well but look weak next to nearby settings."
            "</p>"
            "<table class='data'><thead><tr>"
            "<th>Settings</th><th>Net profit</th><th>Why flagged</th></tr></thead>"
            f"<tbody>{isolated}</tbody></table>"
        )
        if isolated
        else "<p class='note'>No isolated lucky peaks detected in the grid.</p>"
    )
    return f"""
    <section class="panel" id="parameter">
      <h2>Parameter comparison</h2>
      {
        _section_intro(
            "We run the same strategy with different input settings on the same historical data. "
            "This shows whether results are stable across reasonable choices, or depend on one "
            "lucky combination."
        )
    }
      <h3>Top settings by profit</h3>
      <table class="data">
        <thead>
          <tr>
            <th>Rank</th><th>Settings</th><th>Net profit</th><th>Max drawdown</th><th>Trades</th>
          </tr>
        </thead>
        <tbody>{ranking_rows}</tbody>
      </table>
      {heatmaps}
      {isolated_table}
    </section>
    """


def _isolated_reason(reason: str) -> str:
    lowered = reason.lower()
    if "local maximum" in lowered and "negative" in lowered:
        return "Best among neighbors, but all neighbors still lose money"
    if "neighbor" in lowered:
        return "Much better than nearby settings"
    if "isolated" in lowered:
        return "Looks like an isolated peak"
    return reason.replace("_", " ")


def _heatmap_html(heatmap: ParameterHeatmapView) -> str:
    flat_values = [value for row in heatmap.values for value in row if value is not None]
    if not flat_values:
        return ""
    min_value = min(flat_values)
    max_value = max(flat_values)
    cells: list[str] = []
    for y_index, row in enumerate(heatmap.values):
        y_label = (
            heatmap.y_values[y_index]
            if heatmap.y_values is not None and y_index < len(heatmap.y_values)
            else ""
        )
        if y_label:
            cells.append(
                f"<div class='heatmap-axis'>"
                f"{html.escape(format_axis_value(heatmap.y_axis or '', y_label))}"
                f"</div>"
            )
        for value in row:
            color = _heatmap_color(value, min_value, max_value)
            label = "—" if value is None else format_significant(value)
            cells.append(
                f"<div class='heatmap-cell' style='background:{color}'>{html.escape(label)}</div>"
            )
    x_headers = "".join(
        f"<div class='heatmap-axis'>{html.escape(format_axis_value(heatmap.x_axis, value))}</div>"
        for value in heatmap.x_values
    )
    columns = len(heatmap.x_values) + (1 if heatmap.y_values is not None else 0)
    y_axis_label = f" x {html.escape(format_axis_name(heatmap.y_axis))}" if heatmap.y_axis else ""
    return f"""
    <h3>{html.escape(format_metric_label(heatmap.metric.value))} heatmap
    ({html.escape(format_axis_name(heatmap.x_axis))}{y_axis_label})</h3>
    <p class="note">Darker green means a better value for this metric.</p>
    <div class="heatmap" style="grid-template-columns: repeat({columns}, minmax(64px, auto));">
      {x_headers}
      {"".join(cells)}
    </div>
    """


def _heatmap_color(value: float | None, min_value: float, max_value: float) -> str:
    if value is None:
        return "#f1f5f9"
    t = 0.5 if max_value == min_value else (value - min_value) / (max_value - min_value)
    red = int(248 - t * 120)
    green = int(180 + t * 60)
    blue = int(180 + t * 40)
    return f"rgb({red},{green},{blue})"


def _walk_forward_section(
    view_model: RobustnessReportViewModel,
    config_lookup: dict[str, dict[str, str]],
) -> str:
    wf = view_model.walk_forward
    if wf is None:
        return ""
    rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(format_fold_label(evaluation.fold.fold_id))}</td>"
            f"<td>{html.escape(format_parameter_settings(evaluation.selection.parameter_overrides))}</td>"
            f"<td class='num'>{html.escape(format_money(evaluation.selection.train_net_pnl))}</td>"
            f"<td class='num'>{html.escape(format_money(evaluation.oos_summary.net_pnl))}</td>"
            "</tr>"
        )
        for evaluation in wf.fold_evaluations
    )
    return f"""
    <section class="panel" id="walk-forward">
      <h2>Walk-forward validation</h2>
      {
        _section_intro(
            "This mimics real research workflow: pick the best settings using only past data, "
            "then measure performance on the next unseen period. Repeating this across several "
            "periods shows whether the edge survives outside the training window."
        )
    }
      <table class="data">
        <thead>
          <tr>
            <th>Period</th><th>Chosen settings</th><th>Training profit</th><th>Unseen profit</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <div class="chart-box">
        <div class="chart-title">Combined equity on unseen periods only</div>
        <div id="chart-wf-equity" class="chart-host"></div>
      </div>
    </section>
    """


def _stress_section(view_model: RobustnessReportViewModel) -> str:
    stress = view_model.stress
    if stress is None:
        return ""
    rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(format_scenario_label(row.scenario_id))}</td>"
            f"<td class='num'>"
            f"{html.escape(format_money(row.net_pnl) if row.net_pnl is not None else '—')}"
            f"</td>"
            f"<td class='num'>"
            f"{html.escape(_format_optional_money(row.delta_net_pnl))}"
            f"</td>"
            "</tr>"
        )
        for row in stress.rows
    )
    return f"""
    <section class="panel" id="stress">
      <h2>Stress tests</h2>
      {
        _section_intro(
            "Stress tests ask a simple question: what happens when reality is a bit worse than "
            "assumed? We rerun the strategy under tougher conditions such as higher trading "
            "costs or removing the single best trade."
        )
    }
      <p class="note">
        Baseline profit: <strong>{html.escape(format_money(stress.baseline_net_pnl))}</strong>
      </p>
      <table class="data">
        <thead>
          <tr>
            <th>Scenario</th><th>Profit after stress</th><th>Change vs baseline</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _monte_carlo_section(view_model: RobustnessReportViewModel) -> str:
    mc = view_model.monte_carlo
    if mc is None:
        return ""
    dist_rows = "".join(
        (
            "<tr>"
            f"<td>Trade-order shuffle</td>"
            f"<td class='num'>{html.escape(format_money(summary.p5_terminal_equity))}</td>"
            f"<td class='num'>{html.escape(format_money(summary.p50_terminal_equity))}</td>"
            f"<td class='num'>{html.escape(format_money(summary.p95_terminal_equity))}</td>"
            "</tr>"
        )
        for summary in mc.distribution_summaries
    )
    tail_rows = "".join(
        (
            "<tr>"
            f"<td>Trade-order shuffle</td>"
            f"<td class='num'>"
            f"{html.escape(format_probability(metrics.probability_terminal_pnl_negative))}"
            f"</td>"
            f"<td class='num'>"
            f"{html.escape(format_probability(metrics.probability_max_drawdown_exceeds_threshold))}"
            f"</td>"
            "</tr>"
        )
        for metrics in mc.tail_probabilities
    )
    return f"""
    <section class="panel" id="monte-carlo">
      <h2>Monte Carlo simulation</h2>
      {
        _section_intro(
            "We keep the same trades but reshuffle their order many times. If results swing "
            "wildly, the strategy may depend on lucky sequencing rather than a durable edge. "
            "This is a sequencing-risk check, not a forecast of future fills."
        )
    }
      <table class="data">
        <thead>
          <tr>
            <th>Method</th><th>Pessimistic (5%)</th><th>Typical (50%)</th><th>Optimistic (95%)</th>
          </tr>
        </thead>
        <tbody>{dist_rows}</tbody>
      </table>
      <table class="data">
        <thead>
          <tr>
            <th>Method</th><th>Chance of ending in loss</th><th>Chance of deep drawdown</th>
          </tr>
        </thead>
        <tbody>{tail_rows}</tbody>
      </table>
      <div class="chart-box">
        <div class="chart-title">Equity range across shuffled trade orders</div>
        <div id="chart-mc-envelope" class="chart-host"></div>
      </div>
    </section>
    """


def _diagnostics_section(view_model: RobustnessReportViewModel) -> str:
    diag = view_model.diagnostics
    if diag is None:
        return ""
    buckets = "".join(
        (
            "<tr>"
            f"<td>{html.escape(_bucket_label(bucket.bucket_id))}</td>"
            f"<td class='num'>{bucket.trade_count}</td>"
            f"<td class='num'>{html.escape(format_money(bucket.net_pnl))}</td>"
            "</tr>"
        )
        for bucket in diag.temporal_stability.buckets
    )
    degradation = ""
    if diag.is_oos_degradation is not None:
        deg_rows = "".join(
            (
                "<tr>"
                f"<td>{html.escape(format_fold_label(row.fold_id))}</td>"
                f"<td class='num'>{html.escape(format_money(row.train_net_pnl))}</td>"
                f"<td class='num'>{html.escape(format_money(row.oos_net_pnl))}</td>"
                f"<td class='num'>{html.escape(format_money(row.degradation_delta))}</td>"
                "</tr>"
            )
            for row in diag.is_oos_degradation.fold_rows
        )
        degradation = f"""
        <h3>Training vs unseen performance</h3>
        <p class="note">Large drops from training to unseen periods can signal overfitting.</p>
        <table class="data">
          <thead>
            <tr><th>Period</th><th>Training profit</th><th>Unseen profit</th><th>Change</th></tr>
          </thead>
          <tbody>{deg_rows}</tbody>
        </table>
        """
    top_trades_share = abs(diag.pnl_concentration.top_trades_share)
    top_trades_kpi = _kpi(
        "Profit from top trades",
        format_share(top_trades_share),
        top_trades_share <= Decimal("0.5"),
    )
    bucket_mode = diag.temporal_stability.bucket_mode.lower()
    top_days_kpi = _kpi(
        "Profit from top days",
        format_share(abs(diag.pnl_concentration.top_days_share)),
        None,
    )
    spread_kpi = _kpi(
        "Profit spread across periods",
        format_money(diag.temporal_stability.net_pnl_range),
        None,
    )
    return f"""
    <section class="panel" id="diagnostics">
      <h2>Statistical health checks</h2>
      {
        _section_intro(
            "These checks look for red flags that a good headline profit can hide: too much "
            "money coming from a handful of trades or days, or profits that disappear when "
            "results are viewed period by period."
        )
    }
      <div class="kpi-grid">
        {top_trades_kpi}
        {top_days_kpi}
        {spread_kpi}
      </div>
      <h3>Profit by {html.escape(bucket_mode)}</h3>
      <table class="data">
        <thead><tr><th>Period</th><th>Trades</th><th>Net profit</th></tr></thead>
        <tbody>{buckets}</tbody>
      </table>
      {degradation}
    </section>
    """


def _bucket_label(bucket_id: str) -> str:
    if bucket_id.startswith("month:"):
        return bucket_id.removeprefix("month:")
    if bucket_id.startswith("week:"):
        return bucket_id.removeprefix("week:")
    return bucket_id.replace("_", " ")


def _assumptions_section(view_model: RobustnessReportViewModel) -> str:
    gates = "".join(
        (
            "<tr>"
            f"<td>{html.escape(format_gate_label(gate.gate_id))}</td>"
            f"<td>{'Pass' if gate.passed else 'Fail'}</td>"
            f"<td>{'Critical' if gate.severity == 'HARD' else 'Advisory'}</td>"
            f"<td>{html.escape(format_gate_message(gate))}</td>"
            "</tr>"
        )
        for gate in view_model.verdict.gate_results
    )
    gate_table = (
        (
            "<table class='data'><thead><tr>"
            "<th>Check</th><th>Result</th><th>Importance</th><th>Explanation</th>"
            f"</tr></thead><tbody>{gates}</tbody></table>"
        )
        if gates
        else "<p class='note'>No pass/fail rules were configured for this experiment.</p>"
    )
    return f"""
    <section class="panel" id="assumptions">
      <h2>Rules and checklist</h2>
      {
        _section_intro(
            "Before running the experiment we set explicit pass/fail rules. Critical checks "
            "must pass for a clean verdict. Advisory checks highlight concerns but may still "
            "allow a conditional pass."
        )
    }
      {gate_table}
      <details class="technical">
        <summary>Technical replay details</summary>
        <p>Assumptions fingerprint: {html.escape(view_model.simulation_assumptions_fingerprint)}</p>
        <p>Framework version: {html.escape(view_model.framework_version)}</p>
        <p>Dataset reference: {html.escape(view_model.dataset_ref)}</p>
      </details>
    </section>
    """


def _report_js() -> str:
    return """
const payload = JSON.parse(document.getElementById('report-data').textContent);

function renderLineChart(containerId, seriesList) {
  const container = document.getElementById(containerId);
  if (!container || !window.LightweightCharts) return;
  const chart = LightweightCharts.createChart(container, {
    layout: { background: { color: '#ffffff' }, textColor: '#334155' },
    grid: { vertLines: { color: '#e2e8f0' }, horzLines: { color: '#e2e8f0' } },
    rightPriceScale: { borderColor: '#cbd5e1' },
    timeScale: { borderColor: '#cbd5e1' },
  });
  seriesList.forEach((spec) => {
    const line = chart.addLineSeries({
      color: spec.color,
      lineWidth: spec.width || 2,
      title: spec.title,
    });
    line.setData(spec.data);
  });
  chart.timeScale().fitContent();
}

if (payload.walk_forward && payload.walk_forward.stitched_oos_equity) {
  const equityRows = payload.walk_forward.stitched_oos_equity.equity_rows || [];
  const data = equityRows.map((row, index) => ({
    time: index + 1,
    value: Number(row.equity),
  }));
  renderLineChart('chart-wf-equity', [{ title: 'Unseen-period equity', color: '#1d4ed8', data }]);
}

if (payload.monte_carlo && payload.monte_carlo.method_results) {
  const bootstrap = payload.monte_carlo.method_results.find(
    (item) => item.method === 'TRADE_BOOTSTRAP',
  ) || payload.monte_carlo.method_results[0];
  if (bootstrap && bootstrap.percentile_equity) {
    const p50 = bootstrap.percentile_equity.map((point) => ({
      time: point.trade_index + 1,
      value: Number(point.p50),
    }));
    const p5 = bootstrap.percentile_equity.map((point) => ({
      time: point.trade_index + 1,
      value: Number(point.p5),
    }));
    const p95 = bootstrap.percentile_equity.map((point) => ({
      time: point.trade_index + 1,
      value: Number(point.p95),
    }));
    renderLineChart('chart-mc-envelope', [
      { title: 'Pessimistic', color: '#f87171', width: 1, data: p5 },
      { title: 'Typical', color: '#1d4ed8', width: 2, data: p50 },
      { title: 'Optimistic', color: '#22c55e', width: 1, data: p95 },
    ]);
  }
}
"""
