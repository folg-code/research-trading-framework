"""Tests for Binance futures live feed smoke normalization."""

import json
from pathlib import Path
from typing import cast

from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesSmokeConfig,
    BinanceFuturesStreamEndpoint,
    BinanceFuturesWebSocketMessage,
    normalize_smoke_message,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "binance"


def _load_fixture(name: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8")),
    )


def test_smoke_config_normalizes_symbol_and_builds_mvp_streams() -> None:
    config = BinanceFuturesSmokeConfig(symbol=" btcusdt ", duration_seconds=1, max_messages=1)

    assert config.symbol == "BTCUSDT"
    assert [stream.name for stream in config.streams()] == [
        "btcusdt@kline_1m",
        "btcusdt@bookTicker",
    ]


def test_normalize_smoke_message_maps_book_ticker_payload() -> None:
    payload = _load_fixture("usdm_book_ticker.json")
    message = BinanceFuturesWebSocketMessage(
        endpoint=BinanceFuturesStreamEndpoint.PUBLIC,
        url="wss://fstream.binance.com/public/stream?streams=btcusdt@bookTicker",
        payload=payload,
    )

    normalized = normalize_smoke_message(message)

    assert normalized is not None
    assert normalized["event"] == "book_ticker"
    assert normalized["symbol"] == "BTCUSDT"
    assert normalized["bid_price"] == "65009.90"
    assert normalized["ask_price"] == "65010.00"


def test_normalize_smoke_message_maps_only_closed_kline_payloads() -> None:
    closed_message = BinanceFuturesWebSocketMessage(
        endpoint=BinanceFuturesStreamEndpoint.MARKET,
        url="wss://fstream.binance.com/market/stream?streams=btcusdt@kline_1m",
        payload=_load_fixture("usdm_kline_1m_closed.json"),
    )
    open_payload = {
        "stream": "btcusdt@kline_1m",
        "data": _load_fixture("usdm_kline_1m_open.json"),
    }
    open_message = BinanceFuturesWebSocketMessage(
        endpoint=BinanceFuturesStreamEndpoint.MARKET,
        url="wss://fstream.binance.com/market/stream?streams=btcusdt@kline_1m",
        payload=open_payload,
    )

    normalized = normalize_smoke_message(closed_message)

    assert normalized is not None
    assert normalized["event"] == "closed_kline_1m"
    assert normalized["symbol"] == "BTCUSDT"
    assert normalized["close"] == "65010.50"
    assert normalize_smoke_message(open_message) is None
