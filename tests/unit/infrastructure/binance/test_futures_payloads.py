"""Tests for Binance USD-M futures payload parsing."""

import json
from pathlib import Path
from typing import cast

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance import (
    parse_book_ticker_payload,
    parse_combined_stream_payload,
    parse_kline_payload,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "binance"


def _load_fixture(name: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8")),
    )


def test_parse_combined_kline_stream_payload() -> None:
    payload = _load_fixture("usdm_kline_1m_closed.json")

    combined = parse_combined_stream_payload(payload)
    kline = parse_kline_payload(payload)

    assert combined.stream == "btcusdt@kline_1m"
    assert kline.event_type == "kline"
    assert kline.symbol == "BTCUSDT"
    assert kline.interval == "1m"
    assert kline.open_price == "65000.10"
    assert kline.close_price == "65010.50"
    assert kline.volume == "42.123"
    assert kline.is_closed


def test_parse_raw_open_kline_payload() -> None:
    payload = _load_fixture("usdm_kline_1m_open.json")

    kline = parse_kline_payload(payload)

    assert kline.symbol == "BTCUSDT"
    assert not kline.is_closed


def test_parse_combined_book_ticker_payload() -> None:
    payload = _load_fixture("usdm_book_ticker.json")

    book_ticker = parse_book_ticker_payload(payload)

    assert book_ticker.symbol == "BTCUSDT"
    assert book_ticker.bid_price == "65009.90"
    assert book_ticker.bid_quantity == "3.250"
    assert book_ticker.ask_price == "65010.00"
    assert book_ticker.ask_quantity == "1.750"


def test_parse_kline_payload_rejects_missing_kline_body() -> None:
    with pytest.raises(ValidationError, match=r"kline\.k"):
        parse_kline_payload({"e": "kline", "E": 1721044860123, "s": "BTCUSDT"})


def test_parse_book_ticker_rejects_missing_required_field() -> None:
    payload = _load_fixture("usdm_book_ticker.json")
    data = dict(cast(dict[str, object], payload["data"]))
    data.pop("a")

    with pytest.raises(ValidationError, match=r"book_ticker\.a"):
        parse_book_ticker_payload(data)
