"""Binance USD-M futures REST helpers for historical closed klines."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any, final
from urllib.request import Request

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance.futures_mapper import map_kline_payload
from trading_framework.infrastructure.providers.binance.futures_payloads import BinanceKlinePayload
from trading_framework.infrastructure.providers.binance.futures_streams import (
    normalize_stream_symbol,
)
from trading_framework.market.models import MarketBar

BINANCE_USDM_REST_BASE_URL = "https://fapi.binance.com"
DEFAULT_KLINES_TIMEOUT_SECONDS = 15.0
_Urlopener = Callable[[Request, float | None], Any]


@final
class BinanceFuturesRestError(ValidationError):
    """Raised when the Binance USD-M REST klines call fails."""


def fetch_closed_klines(
    *,
    symbol: str,
    limit: int,
    interval: str = "1m",
    base_url: str = BINANCE_USDM_REST_BASE_URL,
    timeout_seconds: float = DEFAULT_KLINES_TIMEOUT_SECONDS,
    urlopen: _Urlopener | None = None,
) -> tuple[MarketBar, ...]:
    """Fetch the latest closed USD-M klines and map them to ``MarketBar``.

    Requests ``limit + 1`` rows and drops the newest candle so an in-progress
    open kline is never treated as closed history.
    """
    if limit < 1:
        msg = "limit must be positive"
        raise ValidationError(msg)
    if timeout_seconds <= 0:
        msg = "timeout_seconds must be positive"
        raise ValidationError(msg)
    normalized_symbol = normalize_stream_symbol(symbol).upper()
    query = urllib.parse.urlencode(
        {
            "symbol": normalized_symbol,
            "interval": interval,
            "limit": limit + 1,
        }
    )
    request = Request(
        f"{base_url.rstrip('/')}/fapi/v1/klines?{query}",
        method="GET",
        headers={"Accept": "application/json"},
    )
    opener: Any = urlopen or urllib.request.urlopen
    try:
        with opener(request, timeout=timeout_seconds) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        msg = f"Binance klines HTTP {exc.code}: {detail[:200]}"
        raise BinanceFuturesRestError(msg) from exc
    except urllib.error.URLError as exc:
        msg = f"Binance klines unreachable: {exc.reason}"
        raise BinanceFuturesRestError(msg) from exc
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "Binance klines response is not valid JSON"
        raise BinanceFuturesRestError(msg) from exc
    if not isinstance(payload, list):
        msg = "Binance klines response must be a JSON array"
        raise BinanceFuturesRestError(msg)
    bars = _map_rest_klines(payload, symbol=normalized_symbol, interval=interval)
    if len(bars) < limit:
        # REST returned fewer closed bars than requested (short history).
        return bars
    return bars[-limit:]


def _map_rest_klines(
    rows: Sequence[object],
    *,
    symbol: str,
    interval: str,
) -> tuple[MarketBar, ...]:
    if len(rows) < 2:
        msg = "Binance klines response must include at least two candles"
        raise BinanceFuturesRestError(msg)
    # Drop the newest row — it may still be the open candle.
    closed_rows = rows[:-1]
    bars: list[MarketBar] = []
    for row in closed_rows:
        payload = _rest_row_to_kline_payload(row, symbol=symbol, interval=interval)
        bars.append(map_kline_payload(payload))
    return tuple(bars)


def _rest_row_to_kline_payload(
    row: object,
    *,
    symbol: str,
    interval: str,
) -> BinanceKlinePayload:
    if not isinstance(row, list) or len(row) < 7:
        msg = "Binance kline row must be an array with at least 7 fields"
        raise BinanceFuturesRestError(msg)
    open_time_ms = int(row[0])
    close_time_ms = int(row[6])
    return BinanceKlinePayload(
        event_type="kline",
        event_time_ms=close_time_ms,
        symbol=symbol,
        interval=interval,
        open_time_ms=open_time_ms,
        close_time_ms=close_time_ms,
        open_price=str(row[1]),
        high_price=str(row[2]),
        low_price=str(row[3]),
        close_price=str(row[4]),
        volume=str(row[5]),
        is_closed=True,
    )
