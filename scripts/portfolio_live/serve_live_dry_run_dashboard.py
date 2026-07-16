"""Serve the live BTC futures dry-run portfolio dashboard.

The app is intentionally small: one read-only HTML page plus an API proxy to the public AWS status
endpoint. It is suitable for a VPS behind nginx/Caddy and keeps secrets out of browser JavaScript.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_POLL_SECONDS = 5
DEFAULT_CANDLE_SECONDS = 60
DEFAULT_STALE_AFTER_SECONDS = 180
STATUS_URL_ENV = "TRADING_FRAMEWORK_STATUS_URL"


@dataclass(frozen=True, slots=True)
class LiveDashboardConfig:
    """Runtime configuration for the VPS-hosted live dashboard."""

    status_url: str
    poll_seconds: int = DEFAULT_POLL_SECONDS
    candle_seconds: int = DEFAULT_CANDLE_SECONDS
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS
    use_fixture: bool = False


_CONFIG_KEY = web.AppKey("config", LiveDashboardConfig)
_SESSION_KEY = web.AppKey("session", aiohttp.ClientSession)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the live BTC futures dry-run portfolio dashboard.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--status-url",
        default=os.environ.get(STATUS_URL_ENV, ""),
        help=f"Read-only AWS status endpoint. Defaults to ${STATUS_URL_ENV}.",
    )
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--candle-seconds", type=int, default=DEFAULT_CANDLE_SECONDS)
    parser.add_argument("--stale-after-seconds", type=int, default=DEFAULT_STALE_AFTER_SECONDS)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Serve the bundled fixture instead of proxying the AWS status endpoint.",
    )
    return parser


def create_app(config: LiveDashboardConfig) -> web.Application:
    """Create the aiohttp web app."""
    app = web.Application()
    app[_CONFIG_KEY] = config
    app.router.add_get("/", _handle_index)
    app.router.add_get("/api/config", _handle_config)
    app.router.add_get("/api/status", _handle_status)
    app.router.add_get("/health", _handle_health)
    app.on_cleanup.append(_cleanup_session)
    return app


async def _handle_index(request: web.Request) -> web.Response:
    config = _config(request)
    return web.Response(
        text=render_dashboard_html(config),
        content_type="text/html",
        headers={"Cache-Control": "no-store"},
    )


async def _handle_config(request: web.Request) -> web.Response:
    config = _config(request)
    return web.json_response(_public_config(config), headers={"Cache-Control": "no-store"})


async def _handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"}, headers={"Cache-Control": "no-store"})


async def _handle_status(request: web.Request) -> web.Response:
    config = _config(request)
    if config.use_fixture or not config.status_url:
        return web.json_response(
            _fixture_payload(),
            headers={"Cache-Control": "no-store", "X-Trading-Framework-Source": "fixture"},
        )

    session = await _client_session(request.app)
    try:
        async with session.get(
            config.status_url,
            headers={"Accept": "application/json"},
        ) as response:
            payload = await response.text()
            content_type = response.headers.get("Content-Type", "application/json")
            return web.Response(
                status=response.status,
                text=payload,
                content_type=content_type.split(";", maxsplit=1)[0],
                headers={
                    "Cache-Control": "no-store",
                    "X-Trading-Framework-Source": "aws-status-api",
                },
            )
    except TimeoutError:
        return _gateway_error("status endpoint timed out")
    except aiohttp.ClientError as exc:
        return _gateway_error(f"status endpoint unavailable: {exc}")


def _gateway_error(message: str) -> web.Response:
    return web.json_response(
        {"error": message, "fixture": _fixture_payload()},
        status=502,
        headers={"Cache-Control": "no-store"},
    )


def _fixture_payload() -> dict[str, object]:
    from scripts.demo.run_portfolio_demo import _live_dry_run_fixture_payload

    return _live_dry_run_fixture_payload()


def _public_config(config: LiveDashboardConfig) -> dict[str, Any]:
    return {
        "pollSeconds": config.poll_seconds,
        "candleSeconds": config.candle_seconds,
        "staleAfterSeconds": config.stale_after_seconds,
        "source": "fixture" if config.use_fixture or not config.status_url else "aws-status-api",
    }


def _config(request: web.Request) -> LiveDashboardConfig:
    return request.app[_CONFIG_KEY]


async def _client_session(app: web.Application) -> aiohttp.ClientSession:
    session = app.get(_SESSION_KEY)
    if session is None or session.closed:
        timeout = aiohttp.ClientTimeout(total=8)
        session = aiohttp.ClientSession(timeout=timeout)
        app[_SESSION_KEY] = session
    return session


async def _cleanup_session(app: web.Application) -> None:
    session = app.get(_SESSION_KEY)
    if session is not None and not session.closed:
        await session.close()


def render_dashboard_html(config: LiveDashboardConfig) -> str:
    """Render the live dashboard HTML shell."""
    config_json = json.dumps(_public_config(config), sort_keys=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BTC Futures Dry-Run Live</title>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0f1318;
      --band: #151b21;
      --panel: #1d252d;
      --line: #32404c;
      --text: #eef3f8;
      --muted: #a9b5c1;
      --buy: #39c980;
      --sell: #f06b6b;
      --accent: #67a8ff;
      --warn: #f0b84a;
      --bad: #ef6b73;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      background: var(--band);
      border-bottom: 1px solid var(--line);
      padding: 1rem 1.25rem;
    }}
    .top, main {{
      max-width: 1280px;
      margin: 0 auto;
    }}
    .top {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 1rem;
      align-items: center;
    }}
    h1 {{ margin: 0; font-size: 1.45rem; letter-spacing: 0; }}
    .subtitle {{ margin: 0.25rem 0 0; color: var(--muted); }}
    main {{ padding: 1rem 1.25rem 1.5rem; }}
    .notice {{
      border: 1px solid #695a28;
      background: #201b10;
      color: #f8df9a;
      border-radius: 8px;
      padding: 0.8rem 1rem;
      margin-bottom: 1rem;
      font-weight: 650;
    }}
    .status-row {{
      display: flex;
      gap: 0.65rem;
      justify-content: flex-end;
      flex-wrap: wrap;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0.38rem 0.68rem;
      background: #10161c;
      color: var(--text);
      font-weight: 750;
      white-space: nowrap;
    }}
    .pill.running {{ color: var(--buy); border-color: var(--buy); }}
    .pill.stale, .pill.stopped {{ color: var(--warn); border-color: var(--warn); }}
    .pill.offline, .pill.failed {{ color: var(--bad); border-color: var(--bad); }}
    .pulse {{
      width: 0.7rem;
      height: 0.7rem;
      border-radius: 50%;
      display: inline-block;
      margin-right: 0.35rem;
      background: var(--muted);
    }}
    .pulse.live {{ background: var(--buy); box-shadow: 0 0 0 0.35rem rgba(57, 201, 128, 0.15); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 1rem;
    }}
    section {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 1rem;
    }}
    .wide {{ grid-column: span 12; }}
    .half {{ grid-column: span 6; }}
    .third {{ grid-column: span 4; }}
    h2 {{ margin: 0 0 0.8rem; font-size: 1rem; }}
    .charts {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(0, 0.6fr);
      gap: 1rem;
    }}
    .chart-host {{ height: 430px; min-height: 320px; }}
    .chart-small {{ height: 280px; min-height: 240px; }}
    dl {{
      margin: 0;
      display: grid;
      grid-template-columns: minmax(130px, 0.8fr) minmax(0, 1.2fr);
      gap: 0.55rem;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; font-weight: 650; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ padding: 0.5rem 0.4rem; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-weight: 650; }}
    .table-wrap {{ overflow-x: auto; }}
    .empty, .muted {{ color: var(--muted); }}
    .error {{ color: var(--bad); font-weight: 650; min-height: 1.5rem; }}
    .side-buy {{ color: var(--buy); font-weight: 750; }}
    .side-sell {{ color: var(--sell); font-weight: 750; }}
    @media (max-width: 880px) {{
      .top, .charts {{ grid-template-columns: 1fr; }}
      .half, .third {{ grid-column: span 12; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="top">
      <div>
        <h1>BTC Futures Dry-Run Live</h1>
        <p class="subtitle">VPS-hosted portfolio dashboard fed by the AWS dry-run read model.</p>
      </div>
      <div class="status-row">
        <div id="status-pill" class="pill"><span id="pulse" class="pulse"></span>LOADING</div>
        <div id="source-pill" class="pill">source: {json.loads(config_json)["source"]}</div>
      </div>
    </div>
  </header>
  <main>
    <div class="notice">
      This demo uses live Binance BTCUSDT futures market data. All orders, fills, positions and PnL
      are simulated. No exchange account, API keys or real capital are connected.
    </div>
    <div id="error" class="error"></div>
    <div class="grid">
      <section class="wide">
        <h2>Live Chart</h2>
        <div class="charts">
          <div>
            <div class="muted">
              Candles are built from incoming status updates; simulated fills appear as markers.
            </div>
            <div id="chart-price" class="chart-host"></div>
          </div>
          <div>
            <div class="muted">Paper equity updates as new status snapshots arrive.</div>
            <div id="chart-equity" class="chart-host chart-small"></div>
          </div>
        </div>
      </section>
      <section class="third"><h2>Runtime</h2><dl id="runtime"></dl></section>
      <section class="third"><h2>Market</h2><dl id="market"></dl></section>
      <section class="third"><h2>Paper Account</h2><dl id="account"></dl></section>
      <section class="half"><h2>Current Paper Position</h2><dl id="position"></dl></section>
      <section class="half"><h2>Last Trades</h2><div id="fills"></div></section>
      <section class="wide"><h2>Recent Orders</h2><div id="orders"></div></section>
    </div>
  </main>
  <script id="dashboard-config" type="application/json">{config_json}</script>
  <script>{_dashboard_javascript()}</script>
</body>
</html>
"""


def _dashboard_javascript() -> str:
    return r"""
const config = JSON.parse(document.getElementById('dashboard-config').textContent);
const candles = new Map();
const equityPoints = [];
let priceChart;
let priceSeries;
let equityChart;
let equitySeries;
let seenFillIds = new Set();

function text(value) {
  return value === null || value === undefined || value === '' ? 'n/a' : String(value);
}

function numberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function unixSeconds(iso) {
  const parsed = Date.parse(iso || '');
  return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : null;
}

function bucketTime(iso) {
  const value = unixSeconds(iso);
  if (value === null) return null;
  return Math.floor(value / config.candleSeconds) * config.candleSeconds;
}

function upsertCandle(time, price) {
  if (time === null || price === null) return;
  const existing = candles.get(time);
  if (!existing) {
    candles.set(time, { time, open: price, high: price, low: price, close: price });
    return;
  }
  existing.high = Math.max(existing.high, price);
  existing.low = Math.min(existing.low, price);
  existing.close = price;
}

function upsertEquity(time, equity) {
  if (time === null || equity === null) return;
  const index = equityPoints.findIndex((point) => point.time === time);
  const point = { time, value: equity };
  if (index >= 0) equityPoints[index] = point;
  else equityPoints.push(point);
  equityPoints.sort((left, right) => left.time - right.time);
  while (equityPoints.length > 500) equityPoints.shift();
}

function seedHistory(payload) {
  for (const row of payload.price_history || []) {
    upsertCandle(bucketTime(row.time), numberOrNull(row.price));
  }
  for (const row of payload.equity_history || []) {
    upsertEquity(unixSeconds(row.time), numberOrNull(row.equity));
  }
}

function appendSnapshot(payload) {
  const price = numberOrNull(payload.last_price);
  const eventTime = payload.last_market_event_at || payload.generated_at;
  upsertCandle(bucketTime(eventTime), price);
  upsertEquity(unixSeconds(payload.generated_at || payload.last_heartbeat_at || eventTime),
    numberOrNull(payload.paper_equity));
}

function ensureCharts() {
  if (!window.LightweightCharts) {
    document.getElementById('chart-price').innerHTML =
      '<p class="empty">Chart library unavailable.</p>';
    return false;
  }
  if (!priceChart) {
    priceChart = LightweightCharts.createChart(document.getElementById('chart-price'), {
      layout: { background: { color: '#1d252d' }, textColor: '#eef3f8' },
      grid: { vertLines: { color: '#2b3540' }, horzLines: { color: '#2b3540' } },
      timeScale: { timeVisible: true, secondsVisible: false },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    });
    priceSeries = priceChart.addCandlestickSeries({
      upColor: '#39c980',
      downColor: '#f06b6b',
      borderVisible: false,
      wickUpColor: '#39c980',
      wickDownColor: '#f06b6b',
    });
  }
  if (!equityChart) {
    equityChart = LightweightCharts.createChart(document.getElementById('chart-equity'), {
      layout: { background: { color: '#1d252d' }, textColor: '#eef3f8' },
      grid: { vertLines: { color: '#2b3540' }, horzLines: { color: '#2b3540' } },
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    equitySeries = equityChart.addLineSeries({ color: '#67a8ff', lineWidth: 2 });
  }
  return true;
}

function fillMarkers(fills) {
  return (fills || []).map((fill) => {
    const side = String(fill.side || '').toLowerCase();
    const price = numberOrNull(fill.price);
    return {
      time: unixSeconds(fill.filled_at),
      position: side === 'buy' ? 'belowBar' : 'aboveBar',
      color: side === 'buy' ? '#39c980' : '#f06b6b',
      shape: side === 'buy' ? 'arrowUp' : 'arrowDown',
      text: `${side.toUpperCase()} ${price === null ? '' : price.toFixed(2)}`,
    };
  }).filter((marker) => marker.time !== null);
}

function renderCharts(payload) {
  seedHistory(payload);
  appendSnapshot(payload);
  if (!ensureCharts()) return;
  priceSeries.setData(Array.from(candles.values()).sort((left, right) => left.time - right.time));
  equitySeries.setData(equityPoints);
  priceSeries.setMarkers(fillMarkers(payload.recent_fills));
  priceChart.timeScale().fitContent();
  equityChart.timeScale().fitContent();
}

function ageMs(iso) {
  const parsed = Date.parse(iso || '');
  return Number.isFinite(parsed) ? Date.now() - parsed : Number.POSITIVE_INFINITY;
}

function effectiveStatus(payload) {
  if (!payload) return 'offline';
  if (ageMs(payload.last_heartbeat_at) > config.staleAfterSeconds * 1000) return 'stale';
  return String(payload.status || 'unknown').toLowerCase();
}

function setStatus(payload, message) {
  const status = message ? 'offline' : effectiveStatus(payload);
  const pill = document.getElementById('status-pill');
  const pulse = document.getElementById('pulse');
  pill.className = `pill ${status}`;
  pulse.className = status === 'running' ? 'pulse live' : 'pulse';
  pill.lastChild.textContent = status.toUpperCase();
  document.getElementById('error').textContent = message || '';
}

function setPairs(id, pairs) {
  document.getElementById(id).innerHTML = pairs
    .map(([key, value]) => `<dt>${key}</dt><dd>${text(value)}</dd>`)
    .join('');
}

function formatSide(side) {
  const value = String(side || '').toLowerCase();
  if (value === 'buy') return '<span class="side-buy">BUY</span>';
  if (value === 'sell') return '<span class="side-sell">SELL</span>';
  return text(side);
}

function rows(items, columns) {
  if (!items || !items.length) return '<p class="empty">No recent simulated records.</p>';
  const head = columns.map((column) => `<th>${column.label}</th>`).join('');
  const body = items.map((item) => `<tr>${columns.map((column) => {
    const value = column.key === 'side' ? formatSide(item[column.key]) : text(item[column.key]);
    return `<td>${value}</td>`;
  }).join('')}</tr>`).join('');
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead>` +
    `<tbody>${body}</tbody></table></div>`;
}

function render(payload) {
  setStatus(payload);
  renderCharts(payload);
  const heartbeatAge = Math.round(ageMs(payload.last_heartbeat_at) / 1000);
  const position = payload.current_position || {};
  setPairs('runtime', [
    ['Runtime id', payload.runtime_id],
    ['Mode', payload.mode],
    ['Provider', payload.provider],
    ['Status', payload.status],
    ['Last heartbeat', payload.last_heartbeat_at],
    ['Heartbeat age', `${heartbeatAge}s`],
  ]);
  setPairs('market', [
    ['Symbol', payload.symbol],
    ['Last price', payload.last_price],
    ['Last market event', payload.last_market_event_at],
    ['Current signal', payload.current_signal],
  ]);
  setPairs('account', [
    ['Paper equity', payload.paper_equity],
    ['Realized PnL', payload.realized_pnl],
    ['Unrealized PnL', payload.unrealized_pnl],
    ['Simulated', payload.simulated],
  ]);
  setPairs('position', [
    ['Symbol', position.symbol],
    ['Side', position.side],
    ['Quantity', position.quantity],
    ['Average entry', position.average_entry_price],
    ['Mark price', position.mark_price],
    ['Unrealized PnL', position.unrealized_pnl],
    ['Updated', position.updated_at],
  ]);
  document.getElementById('fills').innerHTML = rows(payload.recent_fills || [], [
    { key: 'filled_at', label: 'Filled' },
    { key: 'side', label: 'Side' },
    { key: 'quantity', label: 'Qty' },
    { key: 'price', label: 'Price' },
    { key: 'order_id', label: 'Order' },
  ]);
  document.getElementById('orders').innerHTML = rows(payload.recent_orders || [], [
    { key: 'created_at', label: 'Created' },
    { key: 'side', label: 'Side' },
    { key: 'quantity', label: 'Qty' },
    { key: 'status', label: 'Status' },
    { key: 'order_id', label: 'Order' },
  ]);
  for (const fill of payload.recent_fills || []) {
    if (!seenFillIds.has(fill.fill_id)) {
      seenFillIds.add(fill.fill_id);
      console.info('new simulated fill', fill);
    }
  }
}

async function refresh() {
  try {
    const response = await fetch('/api/status', { cache: 'no-store' });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `status ${response.status}`);
    render(payload);
  } catch (error) {
    setStatus(null, `Status feed unavailable: ${error.message}`);
  }
}

refresh();
window.setInterval(refresh, config.pollSeconds * 1000);
"""


async def _run_app(args: argparse.Namespace) -> None:
    config = LiveDashboardConfig(
        status_url=args.status_url.strip(),
        poll_seconds=args.poll_seconds,
        candle_seconds=args.candle_seconds,
        stale_after_seconds=args.stale_after_seconds,
        use_fixture=args.fixture,
    )
    runner = web.AppRunner(create_app(config))
    await runner.setup()
    site = web.TCPSite(runner, args.host, args.port)
    await site.start()
    print(f"Serving live dry-run dashboard on http://{args.host}:{args.port}", flush=True)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is not None:
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await runner.cleanup()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    asyncio.run(_run_app(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
