"""Binance provider adapters."""

from trading_framework.infrastructure.providers.binance.futures_mapper import (
    map_book_ticker_payload,
    map_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    BinanceBookTickerPayload,
    BinanceCombinedStreamPayload,
    BinanceKlinePayload,
    parse_book_ticker_payload,
    parse_combined_stream_payload,
    parse_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_streams import (
    BINANCE_USDM_MAX_STREAMS_PER_CONNECTION,
    BINANCE_USDM_WS_BASE_URL,
    BinanceFuturesStream,
    BinanceFuturesStreamEndpoint,
    book_ticker_stream,
    btcusdt_mvp_streams,
    build_combined_stream_url,
    build_stream_urls_by_endpoint,
    group_streams_by_endpoint,
    kline_1m_stream,
    normalize_stream_symbol,
)

__all__ = [
    "BINANCE_USDM_MAX_STREAMS_PER_CONNECTION",
    "BINANCE_USDM_WS_BASE_URL",
    "BinanceBookTickerPayload",
    "BinanceCombinedStreamPayload",
    "BinanceFuturesStream",
    "BinanceFuturesStreamEndpoint",
    "BinanceKlinePayload",
    "book_ticker_stream",
    "btcusdt_mvp_streams",
    "build_combined_stream_url",
    "build_stream_urls_by_endpoint",
    "group_streams_by_endpoint",
    "kline_1m_stream",
    "map_book_ticker_payload",
    "map_kline_payload",
    "normalize_stream_symbol",
    "parse_book_ticker_payload",
    "parse_combined_stream_payload",
    "parse_kline_payload",
]
