"""Tests for Binance USD-M futures market stream subscriptions."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance import (
    BINANCE_USDM_MAX_STREAMS_PER_CONNECTION,
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


def test_normalize_stream_symbol_uses_lowercase_binance_symbol() -> None:
    assert normalize_stream_symbol(" BTCUSDT ") == "btcusdt"

    with pytest.raises(ValidationError, match="symbol"):
        normalize_stream_symbol("   ")


def test_mvp_streams_use_correct_routed_endpoints() -> None:
    market_stream, public_stream = btcusdt_mvp_streams()

    assert market_stream == BinanceFuturesStream(
        name="btcusdt@kline_1m",
        endpoint=BinanceFuturesStreamEndpoint.MARKET,
    )
    assert public_stream == BinanceFuturesStream(
        name="btcusdt@bookTicker",
        endpoint=BinanceFuturesStreamEndpoint.PUBLIC,
    )


def test_build_combined_stream_url_for_market_endpoint() -> None:
    url = build_combined_stream_url(
        BinanceFuturesStreamEndpoint.MARKET,
        (kline_1m_stream("BTCUSDT"),),
    )

    assert url == "wss://fstream.binance.com/market/stream?streams=btcusdt@kline_1m"


def test_build_stream_urls_by_endpoint_splits_public_and_market_streams() -> None:
    urls = build_stream_urls_by_endpoint(btcusdt_mvp_streams())

    assert urls == {
        BinanceFuturesStreamEndpoint.MARKET: (
            "wss://fstream.binance.com/market/stream?streams=btcusdt@kline_1m"
        ),
        BinanceFuturesStreamEndpoint.PUBLIC: (
            "wss://fstream.binance.com/public/stream?streams=btcusdt@bookTicker"
        ),
    }


def test_group_streams_by_endpoint_preserves_stream_order_per_endpoint() -> None:
    grouped = group_streams_by_endpoint(
        (
            kline_1m_stream("BTCUSDT"),
            kline_1m_stream("ETHUSDT"),
            book_ticker_stream("BTCUSDT"),
        )
    )

    assert [stream.name for stream in grouped[BinanceFuturesStreamEndpoint.MARKET]] == [
        "btcusdt@kline_1m",
        "ethusdt@kline_1m",
    ]
    assert [stream.name for stream in grouped[BinanceFuturesStreamEndpoint.PUBLIC]] == [
        "btcusdt@bookTicker",
    ]


def test_build_combined_stream_url_rejects_mixed_endpoints() -> None:
    with pytest.raises(ValidationError, match="requested endpoint"):
        build_combined_stream_url(
            BinanceFuturesStreamEndpoint.MARKET,
            btcusdt_mvp_streams(),
        )


def test_build_combined_stream_url_rejects_empty_and_oversized_stream_sets() -> None:
    with pytest.raises(ValidationError, match="at least one stream"):
        build_combined_stream_url(BinanceFuturesStreamEndpoint.MARKET, ())

    oversized_streams = tuple(
        kline_1m_stream(f"BTCUSDT_{index}")
        for index in range(BINANCE_USDM_MAX_STREAMS_PER_CONNECTION + 1)
    )
    with pytest.raises(ValidationError, match="connection limit"):
        build_combined_stream_url(BinanceFuturesStreamEndpoint.MARKET, oversized_streams)
