"""TradingView Lightweight Charts helpers for Streamlit OHLCV views."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import streamlit.components.v1 as components

from dashboard_app.contracts import TradeView
from dashboard_app.query.service import OhlcvBarRow

_LIGHTWEIGHT_CHARTS_CDN = (
    "https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"
)

MarkerShape = Literal["arrowUp", "arrowDown", "circle", "square"]
MarkerPosition = Literal["aboveBar", "belowBar", "inBar"]


@dataclass(frozen=True, slots=True)
class CandlePoint:
    """One Lightweight Charts candlestick point (unix seconds)."""

    time: int
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True, slots=True)
class ChartMarker:
    """One Lightweight Charts marker on a candle series."""

    time: int
    position: MarkerPosition
    color: str
    shape: MarkerShape
    text: str


def to_unix_seconds(value: datetime) -> int:
    """Convert a timezone-aware or naive UTC datetime to unix seconds."""
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return int(aware.timestamp())


def candles_from_ohlcv_bars(bars: Sequence[OhlcvBarRow]) -> list[CandlePoint]:
    """Map query OHLCV rows to unique ascending candle points."""
    points: list[CandlePoint] = []
    seen: set[int] = set()
    for bar in bars:
        time = to_unix_seconds(bar.observed_at_utc)
        if time in seen:
            continue
        seen.add(time)
        points.append(
            CandlePoint(
                time=time,
                open=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                close=float(bar.close),
            )
        )
    points.sort(key=lambda point: point.time)
    return points


def candles_from_status_bars(recent_bars: object) -> list[CandlePoint]:
    """Map live-paper ``recent_bars`` payload rows to candle points."""
    if not isinstance(recent_bars, list):
        return []
    points: list[CandlePoint] = []
    seen: set[int] = set()
    for item in recent_bars:
        if not isinstance(item, Mapping):
            continue
        observed = _parse_utc(item.get("observed_at"))
        open_ = _as_float(item.get("open"))
        high = _as_float(item.get("high"))
        low = _as_float(item.get("low"))
        close = _as_float(item.get("close"))
        if observed is None or None in (open_, high, low, close):
            continue
        time = to_unix_seconds(observed)
        if time in seen:
            continue
        seen.add(time)
        points.append(CandlePoint(time=time, open=open_, high=high, low=low, close=close))
    points.sort(key=lambda point: point.time)
    return points


def markers_for_trade(trade: TradeView) -> list[ChartMarker]:
    """Build entry/exit markers for one selected strategy trade."""
    markers: list[ChartMarker] = []
    side = trade.side.lower()
    long_side = side in {"long", "buy"}
    if trade.entry_price is not None:
        markers.append(
            ChartMarker(
                time=to_unix_seconds(trade.entry_at_utc),
                position="belowBar" if long_side else "aboveBar",
                color="#22c55e" if long_side else "#ef4444",
                shape="arrowUp" if long_side else "arrowDown",
                text=f"{trade.side} entry",
            )
        )
    if trade.exit_at_utc is not None and trade.exit_price is not None:
        markers.append(
            ChartMarker(
                time=to_unix_seconds(trade.exit_at_utc),
                position="aboveBar" if long_side else "belowBar",
                color="#f59e0b",
                shape="arrowDown" if long_side else "arrowUp",
                text="exit",
            )
        )
    markers.sort(key=lambda marker: marker.time)
    return markers


def markers_for_fills(recent_fills: object) -> list[ChartMarker]:
    """Build markers from live-paper ``recent_fills`` rows."""
    if not isinstance(recent_fills, list):
        return []
    markers: list[ChartMarker] = []
    for row in recent_fills:
        if not isinstance(row, Mapping):
            continue
        filled_at = _parse_utc(row.get("filled_at") or row.get("event_at"))
        price = _as_float(row.get("price") or row.get("fill_price"))
        if filled_at is None or price is None:
            continue
        side = str(row.get("side") or "fill").lower()
        buy = side in {"buy", "long", "bid"}
        markers.append(
            ChartMarker(
                time=to_unix_seconds(filled_at),
                position="belowBar" if buy else "aboveBar",
                color="#38bdf8",
                shape="circle",
                text=side,
            )
        )
    markers.sort(key=lambda marker: marker.time)
    return markers


def render_lightweight_candlestick(
    candles: Sequence[CandlePoint],
    *,
    markers: Sequence[ChartMarker] = (),
    height: int = 440,
    title: str | None = None,
) -> None:
    """Render an interactive Lightweight Charts candlestick in Streamlit."""
    chart_id = f"lwc-{uuid.uuid4().hex}"
    payload = {
        "candles": [
            {
                "time": candle.time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            }
            for candle in candles
        ],
        "markers": [
            {
                "time": marker.time,
                "position": marker.position,
                "color": marker.color,
                "shape": marker.shape,
                "text": marker.text,
            }
            for marker in markers
        ],
    }
    payload_json = json.dumps(payload)
    title_html = ""
    if title:
        title_html = (
            "<div style='color:#e2e8f0;font:600 14px/1.4 system-ui,sans-serif;"
            f"margin:0 0 8px'>{_escape(title)}</div>"
        )
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="{_LIGHTWEIGHT_CHARTS_CDN}"></script>
  <style>
    html, body {{ margin: 0; padding: 0; background: #0e1117; }}
    #{chart_id} {{ width: 100%; height: {height}px; }}
  </style>
</head>
<body>
  {title_html}
  <div id="{chart_id}"></div>
  <script>
    const payload = {payload_json};
    const container = document.getElementById("{chart_id}");
    if (!window.LightweightCharts || !container) {{
      container.textContent = "Lightweight Charts failed to load.";
    }} else if (!payload.candles.length) {{
      container.style.color = "#94a3b8";
      container.style.font = "13px/1.4 system-ui,sans-serif";
      container.style.padding = "24px";
      container.textContent = "No OHLCV bars in this window.";
    }} else {{
      const chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: {height},
        layout: {{
          background: {{ color: "#0e1117" }},
          textColor: "#e2e8f0"
        }},
        grid: {{
          vertLines: {{ color: "#262730" }},
          horzLines: {{ color: "#262730" }}
        }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        rightPriceScale: {{ borderColor: "#3b4252" }},
        timeScale: {{
          borderColor: "#3b4252",
          timeVisible: true,
          secondsVisible: false
        }}
      }});
      const series = chart.addCandlestickSeries({{
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444"
      }});
      series.setData(payload.candles);
      if (payload.markers.length) {{
        series.setMarkers(payload.markers);
      }}
      chart.timeScale().fitContent();
      window.addEventListener("resize", () => {{
        chart.applyOptions({{ width: container.clientWidth }});
      }});
    }}
  </script>
</body>
</html>
"""
    components.html(html, height=height + (36 if title else 8), scrolling=False)


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None
