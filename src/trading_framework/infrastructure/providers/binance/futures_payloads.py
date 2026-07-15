"""Binance USD-M futures WebSocket payload parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, final

from trading_framework.core.exceptions import ValidationError

BINANCE_USDM_WS_BASE_URL = "wss://fstream.binance.com"
BINANCE_USDM_MARKET_STREAM_BASE_URL = f"{BINANCE_USDM_WS_BASE_URL}/market"


def _require_mapping(payload: object, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        msg = f"{context} payload must be a JSON object"
        raise ValidationError(msg)
    return payload


def _require_str(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"{context}.{key} must be a non-empty string"
        raise ValidationError(msg)
    return value


def _require_int(payload: dict[str, Any], key: str, context: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{context}.{key} must be an integer"
        raise ValidationError(msg)
    return value


def _require_bool(payload: dict[str, Any], key: str, context: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        msg = f"{context}.{key} must be a boolean"
        raise ValidationError(msg)
    return value


@final
@dataclass(frozen=True, slots=True)
class BinanceCombinedStreamPayload:
    """Combined stream wrapper: {"stream": name, "data": rawPayload}."""

    stream: str
    data: dict[str, Any]


@final
@dataclass(frozen=True, slots=True)
class BinanceKlinePayload:
    """Raw Binance USD-M futures kline payload."""

    event_type: str
    event_time_ms: int
    symbol: str
    interval: str
    open_time_ms: int
    close_time_ms: int
    open_price: str
    high_price: str
    low_price: str
    close_price: str
    volume: str
    is_closed: bool


@final
@dataclass(frozen=True, slots=True)
class BinanceBookTickerPayload:
    """Raw Binance USD-M futures bookTicker payload."""

    event_time_ms: int
    transaction_time_ms: int
    symbol: str
    bid_price: str
    bid_quantity: str
    ask_price: str
    ask_quantity: str


def unwrap_combined_stream_payload(payload: object) -> dict[str, Any]:
    """Return raw stream data for either combined or raw Binance stream payloads."""
    mapping = _require_mapping(payload, "binance_stream")
    if "stream" not in mapping and "data" not in mapping:
        return mapping
    combined = parse_combined_stream_payload(mapping)
    return combined.data


def parse_combined_stream_payload(payload: object) -> BinanceCombinedStreamPayload:
    """Parse a combined Binance stream wrapper."""
    mapping = _require_mapping(payload, "combined_stream")
    stream = _require_str(mapping, "stream", "combined_stream")
    data = _require_mapping(mapping.get("data"), "combined_stream.data")
    return BinanceCombinedStreamPayload(stream=stream, data=data)


def parse_kline_payload(payload: object) -> BinanceKlinePayload:
    """Parse a raw or combined Binance kline stream payload."""
    mapping = unwrap_combined_stream_payload(payload)
    kline = _require_mapping(mapping.get("k"), "kline.k")
    return BinanceKlinePayload(
        event_type=_require_str(mapping, "e", "kline"),
        event_time_ms=_require_int(mapping, "E", "kline"),
        symbol=_require_str(mapping, "s", "kline"),
        interval=_require_str(kline, "i", "kline.k"),
        open_time_ms=_require_int(kline, "t", "kline.k"),
        close_time_ms=_require_int(kline, "T", "kline.k"),
        open_price=_require_str(kline, "o", "kline.k"),
        high_price=_require_str(kline, "h", "kline.k"),
        low_price=_require_str(kline, "l", "kline.k"),
        close_price=_require_str(kline, "c", "kline.k"),
        volume=_require_str(kline, "v", "kline.k"),
        is_closed=_require_bool(kline, "x", "kline.k"),
    )


def parse_book_ticker_payload(payload: object) -> BinanceBookTickerPayload:
    """Parse a raw or combined Binance bookTicker stream payload."""
    mapping = unwrap_combined_stream_payload(payload)
    return BinanceBookTickerPayload(
        event_time_ms=_require_int(mapping, "E", "book_ticker"),
        transaction_time_ms=_require_int(mapping, "T", "book_ticker"),
        symbol=_require_str(mapping, "s", "book_ticker"),
        bid_price=_require_str(mapping, "b", "book_ticker"),
        bid_quantity=_require_str(mapping, "B", "book_ticker"),
        ask_price=_require_str(mapping, "a", "book_ticker"),
        ask_quantity=_require_str(mapping, "A", "book_ticker"),
    )
