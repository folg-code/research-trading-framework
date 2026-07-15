"""Binance USD-M futures market stream subscription specs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import final
from urllib.parse import quote

from trading_framework.core.exceptions import ValidationError

BINANCE_USDM_WS_BASE_URL = "wss://fstream.binance.com"
BINANCE_USDM_MAX_STREAMS_PER_CONNECTION = 1024


class BinanceFuturesStreamEndpoint(StrEnum):
    """Routed Binance USD-M market stream endpoint."""

    PUBLIC = "public"
    MARKET = "market"


@final
@dataclass(frozen=True, slots=True)
class BinanceFuturesStream:
    """A single Binance USD-M futures stream and its routed endpoint."""

    name: str
    endpoint: BinanceFuturesStreamEndpoint

    def __post_init__(self) -> None:
        stream_name = self.name.strip()
        if not stream_name:
            msg = "stream name must be non-empty"
            raise ValidationError(msg)
        object.__setattr__(self, "name", stream_name)


def normalize_stream_symbol(symbol: str) -> str:
    """Normalize a canonical symbol into Binance stream symbol form."""
    normalized = symbol.strip().lower()
    if not normalized:
        msg = "symbol must be non-empty"
        raise ValidationError(msg)
    return normalized


def kline_1m_stream(symbol: str) -> BinanceFuturesStream:
    """Build the regular-market 1m kline stream spec for a symbol."""
    stream_symbol = normalize_stream_symbol(symbol)
    return BinanceFuturesStream(
        name=f"{stream_symbol}@kline_1m",
        endpoint=BinanceFuturesStreamEndpoint.MARKET,
    )


def book_ticker_stream(symbol: str) -> BinanceFuturesStream:
    """Build the high-frequency public bookTicker stream spec for a symbol."""
    stream_symbol = normalize_stream_symbol(symbol)
    return BinanceFuturesStream(
        name=f"{stream_symbol}@bookTicker",
        endpoint=BinanceFuturesStreamEndpoint.PUBLIC,
    )


def btcusdt_mvp_streams() -> tuple[BinanceFuturesStream, ...]:
    """Return the Sprint 019 BTCUSDT MVP stream set."""
    return (
        kline_1m_stream("BTCUSDT"),
        book_ticker_stream("BTCUSDT"),
    )


def group_streams_by_endpoint(
    streams: tuple[BinanceFuturesStream, ...],
) -> dict[BinanceFuturesStreamEndpoint, tuple[BinanceFuturesStream, ...]]:
    """Group stream specs by routed Binance endpoint."""
    grouped: defaultdict[BinanceFuturesStreamEndpoint, list[BinanceFuturesStream]] = defaultdict(
        list
    )
    for stream in streams:
        grouped[stream.endpoint].append(stream)
    return {endpoint: tuple(endpoint_streams) for endpoint, endpoint_streams in grouped.items()}


def build_combined_stream_url(
    endpoint: BinanceFuturesStreamEndpoint,
    streams: tuple[BinanceFuturesStream, ...],
) -> str:
    """Build a combined stream URL for streams belonging to one routed endpoint."""
    if not streams:
        msg = "at least one stream is required"
        raise ValidationError(msg)
    if len(streams) > BINANCE_USDM_MAX_STREAMS_PER_CONNECTION:
        msg = "stream count exceeds Binance connection limit"
        raise ValidationError(msg)
    if any(stream.endpoint is not endpoint for stream in streams):
        msg = "all streams must belong to the requested endpoint"
        raise ValidationError(msg)

    encoded_streams = "/".join(quote(stream.name, safe="@_!") for stream in streams)
    return f"{BINANCE_USDM_WS_BASE_URL}/{endpoint.value}/stream?streams={encoded_streams}"


def build_stream_urls_by_endpoint(
    streams: tuple[BinanceFuturesStream, ...],
) -> dict[BinanceFuturesStreamEndpoint, str]:
    """Build combined stream URLs grouped by routed endpoint."""
    grouped_streams = group_streams_by_endpoint(streams)
    return {
        endpoint: build_combined_stream_url(endpoint, endpoint_streams)
        for endpoint, endpoint_streams in grouped_streams.items()
    }
