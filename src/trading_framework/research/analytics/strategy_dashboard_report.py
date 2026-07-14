"""Presentation-only HTML dashboard for Strategy Research view models."""

from __future__ import annotations

import html
import json
from decimal import Decimal
from pathlib import Path

from trading_framework.research.analytics.strategy_dashboard import (
    StrategyDashboardMetricWarning,
    StrategyDashboardOverviewKpis,
    StrategyDashboardPerformancePanels,
    StrategyDashboardViewModel,
    strategy_dashboard_view_model_to_dict,
)

_LIGHTWEIGHT_CHARTS_CDN = (
    "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"
)

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
  --positive: #15803d;
  --negative: #b91c1c;
  --accent: #1d4ed8;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
}
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 2.5rem;
}
header { margin-bottom: 1.25rem; }
header h1 { margin: 0 0 0.35rem; font-size: 1.55rem; }
header .meta { color: var(--muted); font-size: 0.92rem; }
section.panel {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin-bottom: 1rem;
}
section.panel h2 {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
}
section.panel h3 {
  margin: 0 0 0.65rem;
  font-size: 0.95rem;
  color: var(--muted);
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
.warning-list {
  display: grid;
  gap: 0.55rem;
}
.warning-item {
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 8px;
  padding: 0.65rem 0.8rem;
  color: #9a3412;
  font-size: 0.88rem;
}
.warning-item strong {
  display: block;
  margin-bottom: 0.15rem;
  font-size: 0.8rem;
}
.chart-grid {
  display: grid;
  gap: 0.85rem;
}
.chart-grid.two-col {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
.chart-box {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.chart-box .chart-title {
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.86rem;
  color: var(--muted);
}
.chart-host { width: 100%; height: 320px; }
.chart-host.tall { height: 420px; }
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
table.data tbody tr { cursor: pointer; }
table.data tbody tr:hover { background: #f8fafc; }
table.data tbody tr.active { background: #eff6ff; }
.bar-chart {
  display: grid;
  gap: 0.45rem;
}
.bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 70px;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.82rem;
}
.bar-track {
  height: 12px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #60a5fa, #1d4ed8);
  border-radius: 999px;
}
.bar-fill.negative {
  background: linear-gradient(90deg, #f87171, #b91c1c);
}
.note { color: var(--muted); font-size: 0.88rem; margin: 0 0 0.75rem; }
"""


def render_strategy_research_dashboard(
    view_model: StrategyDashboardViewModel,
    output_path: Path,
) -> Path:
    """Render a standalone Strategy Research dashboard HTML file.

    Presentation-only: consumes ``StrategyDashboardViewModel`` — no Parquet reads
    or metric recomputation.
    """
    payload = strategy_dashboard_view_model_to_dict(view_model)
    payload_json = json.dumps(payload, indent=2)
    title = f"Strategy Research dashboard — {view_model.run_id}"
    header_meta = (
        f"Strategy: <strong>{html.escape(view_model.strategy_model_id)}</strong> · "
        f"Market: <strong>{html.escape(view_model.market_model_id)}</strong> · "
        f"Signal: <strong>{html.escape(view_model.signal_model_id)}</strong><br>"
        f"Dataset: <strong>{html.escape(view_model.source_dataset_ref)}</strong> · "
        f"Timeframe: <strong>{html.escape(view_model.metadata.evaluation_timeframe)}</strong> · "
        f"Bars: <strong>{view_model.metadata.bar_count}</strong> · "
        f"Assumptions: "
        f"<strong>{html.escape(view_model.simulation_assumptions_fingerprint)}</strong>"
    )
    document = _render_document(
        title=title,
        header_meta=header_meta,
        view_model=view_model,
        payload_json=payload_json,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def _render_document(
    *,
    title: str,
    header_meta: str,
    view_model: StrategyDashboardViewModel,
    payload_json: str,
) -> str:
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
    </header>
    {_warnings_section(view_model.metric_context.warnings)}
    <section class="panel" id="overview">
      <h2>Overview</h2>
      <p class="note">
        Primary KPIs computed from persisted trades and equity facts.
        Read warnings before interpreting ratios.
      </p>
      {_kpi_grid(view_model.overview)}
      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-title">Equity curve</div>
          <div id="chart-equity" class="chart-host"></div>
        </div>
        <div class="chart-box">
          <div class="chart-title">OHLCV with entry / exit markers (pan, zoom, crosshair)</div>
          <div id="chart-ohlcv" class="chart-host tall"></div>
        </div>
      </div>
    </section>
    <section class="panel" id="performance">
      <h2>Performance Analysis</h2>
      <div class="chart-grid two-col">
        <div class="chart-box">
          <div class="chart-title">Drawdown curve</div>
          <div id="chart-drawdown" class="chart-host"></div>
        </div>
        <div>
          <h3>Monthly PnL</h3>
          {_monthly_pnl_bars(view_model.performance)}
        </div>
        <div>
          <h3>Trade PnL histogram</h3>
          {_histogram_bars(view_model.performance)}
        </div>
      </div>
      <h3>Recent trades</h3>
      {_recent_trades_table(view_model.performance)}
    </section>
    <section class="panel" id="conditional">
      <h2>Conditional Analysis</h2>
      <p class="note">
        Model ids are run constants:
        market <strong>{html.escape(view_model.market_model_id)}</strong>,
        signal <strong>{html.escape(view_model.signal_model_id)}</strong>.
        Volatility regime breakdown is deferred.
      </p>
      <div class="chart-grid two-col">
        <div>{_direction_breakdown_table(view_model.performance)}</div>
        <div>{_session_breakdown_table(view_model.performance)}</div>
        <div>{_hour_breakdown_table(view_model.performance)}</div>
      </div>
    </section>
  </div>
  <script id="dashboard-data" type="application/json">{payload_json}</script>
  <script>{_dashboard_js()}</script>
</body>
</html>
"""


def _warnings_section(warnings: tuple[StrategyDashboardMetricWarning, ...]) -> str:
    if not warnings:
        return ""
    items = "".join(
        (
            "<div class='warning-item'>"
            f"<strong>{html.escape(warning.code)}</strong>"
            f"{html.escape(warning.message)}"
            "</div>"
        )
        for warning in warnings
    )
    return (
        "<section class='panel' id='warnings'>"
        "<h2>Interpretation warnings</h2>"
        f"<div class='warning-list'>{items}</div>"
        "</section>"
    )


def _kpi_grid(overview: StrategyDashboardOverviewKpis) -> str:
    cards = [
        ("Net PnL", _fmt_money(overview.net_pnl), _pnl_class(overview.net_pnl)),
        ("Total Return", _fmt_pct(overview.total_return), _return_class(overview.total_return)),
        ("Max Drawdown", _fmt_money(overview.max_drawdown), "negative"),
        ("Current Drawdown", _fmt_money(overview.current_drawdown), "negative"),
        ("Sharpe", _fmt_ratio(overview.sharpe_ratio), ""),
        ("Sortino", _fmt_ratio(overview.sortino_ratio), ""),
        ("Profit Factor", _fmt_ratio(overview.profit_factor), ""),
        ("Expectancy", _fmt_money_optional(overview.expectancy), ""),
        ("Number of Trades", str(overview.trade_count), ""),
        ("Win Rate", _fmt_pct(overview.win_rate), ""),
        ("Average Win", _fmt_money_optional(overview.avg_win), "positive"),
        ("Average Loss", _fmt_money_optional(overview.avg_loss), "negative"),
        ("Total Costs", _fmt_money(overview.total_costs), ""),
    ]
    rendered = "".join(_kpi_card(label, value, css_class) for label, value, css_class in cards)
    return f"<div class='kpi-grid'>{rendered}</div>"


def _kpi_card(label: str, value: str, css_class: str) -> str:
    value_class = f"value {css_class}".strip()
    return (
        "<div class='kpi-card'>"
        f"<div class='label'>{html.escape(label)}</div>"
        f"<div class='{html.escape(value_class)}'>{html.escape(value)}</div>"
        "</div>"
    )


def _monthly_pnl_bars(performance: StrategyDashboardPerformancePanels) -> str:
    if not performance.monthly_pnl:
        return "<p class='note'>No monthly PnL rows.</p>"
    max_abs = max(abs(row.net_pnl) for row in performance.monthly_pnl) or 1.0
    rows = []
    for row in performance.monthly_pnl:
        width = min(abs(row.net_pnl) / max_abs * 100.0, 100.0)
        css = "bar-fill negative" if row.net_pnl < 0 else "bar-fill"
        rows.append(
            "<div class='bar-row'>"
            f"<span>{html.escape(row.month)}</span>"
            f"<div class='bar-track'><div class='{css}' style='width:{width:.1f}%'></div></div>"
            f"<span class='num'>{row.net_pnl:,.2f}</span>"
            "</div>"
        )
    return f"<div class='bar-chart'>{''.join(rows)}</div>"


def _histogram_bars(performance: StrategyDashboardPerformancePanels) -> str:
    if not performance.trade_pnl_histogram:
        return "<p class='note'>No histogram buckets.</p>"
    max_count = max(bucket.count for bucket in performance.trade_pnl_histogram) or 1
    rows = []
    for bucket in performance.trade_pnl_histogram:
        width = bucket.count / max_count * 100.0
        label = f"{bucket.bucket_start:,.0f}…{bucket.bucket_end:,.0f}"
        rows.append(
            "<div class='bar-row'>"
            f"<span>{html.escape(label)}</span>"
            f"<div class='bar-track'><div class='bar-fill' style='width:{width:.1f}%'></div></div>"
            f"<span class='num'>{bucket.count}</span>"
            "</div>"
        )
    return f"<div class='bar-chart'>{''.join(rows)}</div>"


def _recent_trades_table(performance: StrategyDashboardPerformancePanels) -> str:
    if not performance.recent_trades:
        return "<p class='note'>No trades in this run.</p>"
    rows = []
    for trade in performance.recent_trades:
        rows.append(
            "<tr "
            f"data-entry-ts='{html.escape(trade.entry_fill_at.isoformat())}' "
            f"data-exit-ts='{html.escape(trade.exit_fill_at.isoformat())}'>"
            f"<td>{html.escape(trade.trade_id)}</td>"
            f"<td>{html.escape(trade.direction)}</td>"
            f"<td>{html.escape(trade.entry_fill_at.isoformat())}</td>"
            f"<td>{html.escape(trade.exit_fill_at.isoformat())}</td>"
            f"<td class='num'>{trade.net_pnl:,.2f}</td>"
            f"<td class='num'>{trade.bars_held}</td>"
            f"<td>{html.escape(trade.exit_reason)}</td>"
            "</tr>"
        )
    return (
        "<table class='data' id='recent-trades-table'>"
        "<thead><tr>"
        "<th>Trade</th><th>Dir</th><th>Entry</th><th>Exit</th>"
        "<th>Net PnL</th><th>Bars</th><th>Reason</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _direction_breakdown_table(performance: StrategyDashboardPerformancePanels) -> str:
    rows = [
        (row.direction, row.trade_count, row.net_pnl, row.win_rate)
        for row in performance.direction_breakdown
    ]
    return _simple_breakdown_table("Direction", rows)


def _session_breakdown_table(performance: StrategyDashboardPerformancePanels) -> str:
    rows = [
        (row.session, row.trade_count, row.net_pnl, row.win_rate)
        for row in performance.session_breakdown
    ]
    return _simple_breakdown_table("Session", rows)


def _hour_breakdown_table(performance: StrategyDashboardPerformancePanels) -> str:
    return _simple_breakdown_table(
        "Hour (NY)",
        [
            (row.hour_bucket, row.trade_count, row.net_pnl, row.win_rate)
            for row in performance.hour_breakdown
        ],
    )


def _simple_breakdown_table(
    title: str,
    rows_data: list[tuple[str, int, float, float | None]],
) -> str:
    if not rows_data:
        return f"<h3>{html.escape(title)}</h3><p class='note'>No rows.</p>"
    body = []
    for label, trade_count, net_pnl, win_rate in rows_data:
        win_rate_text = "—" if win_rate is None else f"{win_rate * 100:.1f}%"
        body.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td class='num'>{trade_count}</td>"
            f"<td class='num'>{net_pnl:,.2f}</td>"
            f"<td class='num'>{html.escape(win_rate_text)}</td>"
            "</tr>"
        )
    return (
        f"<h3>{html.escape(title)}</h3>"
        "<table class='data'><thead><tr>"
        "<th>Bucket</th><th>Trades</th><th>Net PnL</th><th>Win rate</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _fmt_money(value: Decimal) -> str:
    return f"{value:,.2f}"


def _fmt_money_optional(value: Decimal | None) -> str:
    return "—" if value is None else _fmt_money(value)


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.2f}%"


def _fmt_ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _pnl_class(value: Decimal) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return ""


def _return_class(value: float | None) -> str:
    if value is None:
        return ""
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return ""


def _dashboard_js() -> str:
    return """
const dashboardData = JSON.parse(document.getElementById('dashboard-data').textContent);

function toUnix(iso) {
  return Math.floor(Date.parse(iso) / 1000);
}

function makeChart(elementId, height) {
  const container = document.getElementById(elementId);
  return LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: height || container.clientHeight,
    layout: { background: { color: '#ffffff' }, textColor: '#334155' },
    grid: { vertLines: { color: '#f1f5f9' }, horzLines: { color: '#f1f5f9' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: '#cbd5e1' },
    timeScale: { borderColor: '#cbd5e1', timeVisible: true, secondsVisible: true },
  });
}

const equityChart = makeChart('chart-equity');
const equitySeries = equityChart.addLineSeries({ color: '#1d4ed8', lineWidth: 2 });
equitySeries.setData(
  dashboardData.equity.map((point) => ({
    time: toUnix(point.observed_at),
    value: point.equity,
  })),
);

const drawdownChart = makeChart('chart-drawdown');
const drawdownSeries = drawdownChart.addAreaSeries({
  lineColor: '#b91c1c',
  topColor: 'rgba(185, 28, 28, 0.35)',
  bottomColor: 'rgba(185, 28, 28, 0.05)',
});
drawdownSeries.setData(
  dashboardData.equity.map((point) => ({
    time: toUnix(point.observed_at),
    value: point.drawdown,
  })),
);

const ohlcvChart = makeChart('chart-ohlcv', 420);
const candleSeries = ohlcvChart.addCandlestickSeries({
  upColor: '#16a34a',
  downColor: '#dc2626',
  borderVisible: false,
  wickUpColor: '#16a34a',
  wickDownColor: '#dc2626',
});
candleSeries.setData(
  dashboardData.bars.map((bar) => ({
    time: toUnix(bar.observed_at),
    open: bar.open,
    high: bar.high,
    low: bar.low,
    close: bar.close,
  })),
);

const markers = [];
for (const trade of dashboardData.trades) {
  const entryPosition = trade.direction === 'long' ? 'belowBar' : 'aboveBar';
  const exitPosition = trade.direction === 'long' ? 'aboveBar' : 'belowBar';
  markers.push({
    time: toUnix(trade.entry_fill_at),
    position: entryPosition,
    color: '#1d4ed8',
    shape: 'arrowUp',
    text: `${trade.direction} entry`,
  });
  markers.push({
    time: toUnix(trade.exit_fill_at),
    position: exitPosition,
    color: '#b45309',
    shape: 'arrowDown',
    text: 'exit',
  });
}
markers.sort((left, right) => left.time - right.time);
candleSeries.setMarkers(markers);

function focusTradeRange(entryIso, exitIso) {
  const entryTs = toUnix(entryIso);
  const exitTs = toUnix(exitIso);
  const padding = Math.max(Math.floor((exitTs - entryTs) * 0.35), 300);
  ohlcvChart.timeScale().setVisibleRange({
    from: entryTs - padding,
    to: exitTs + padding,
  });
  equityChart.timeScale().setVisibleRange({
    from: entryTs - padding,
    to: exitTs + padding,
  });
  drawdownChart.timeScale().setVisibleRange({
    from: entryTs - padding,
    to: exitTs + padding,
  });
}

const tradeRows = document.querySelectorAll('#recent-trades-table tbody tr');
tradeRows.forEach((row) => {
  row.addEventListener('click', () => {
    tradeRows.forEach((item) => item.classList.remove('active'));
    row.classList.add('active');
    focusTradeRange(row.dataset.entryTs, row.dataset.exitTs);
  });
});

window.addEventListener('resize', () => {
  ['chart-equity', 'chart-ohlcv', 'chart-drawdown'].forEach((id) => {
    const container = document.getElementById(id);
    const chart = (
      id === 'chart-equity' ? equityChart : id === 'chart-ohlcv' ? ohlcvChart : drawdownChart
    );
    chart.applyOptions({ width: container.clientWidth });
  });
});
"""


__all__ = ["render_strategy_research_dashboard"]
