"""Tests for Binance USD-M futures payload mapping."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance import (
    map_book_ticker_payload,
    map_kline_payload,
    parse_book_ticker_payload,
    parse_kline_payload,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "binance"


def _load_fixture(name: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8")),
    )


def test_map_closed_kline_to_market_bar() -> None:
    payload = parse_kline_payload(_load_fixture("usdm_kline_1m_closed.json"))

    bar = map_kline_payload(payload)

    assert bar.open.value == Decimal("65000.10")
    assert bar.high.value == Decimal("65020.00")
    assert bar.low.value == Decimal("64990.00")
    assert bar.close.value == Decimal("65010.50")
    assert bar.volume.value == 42
    assert bar.observed_at == datetime(2024, 7, 15, 12, 0, tzinfo=UTC)
    assert bar.available_at == datetime(2024, 7, 15, 12, 1, tzinfo=UTC)


def test_map_kline_rejects_open_kline() -> None:
    payload = parse_kline_payload(_load_fixture("usdm_kline_1m_open.json"))

    with pytest.raises(ValidationError, match="closed Binance klines"):
        map_kline_payload(payload)


def test_map_book_ticker_to_best_bid_ask_snapshot() -> None:
    payload = parse_book_ticker_payload(_load_fixture("usdm_book_ticker.json"))

    snapshot = map_book_ticker_payload(payload)

    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.bid_price.value == Decimal("65009.90")
    assert snapshot.ask_price.value == Decimal("65010.00")
    assert snapshot.event_at == datetime(2024, 7, 15, 12, 1, 0, 456000, tzinfo=UTC)
    assert snapshot.received_at == datetime(2024, 7, 15, 12, 1, 0, 457000, tzinfo=UTC)


def test_map_book_ticker_rejects_crossed_bid_ask() -> None:
    payload = parse_book_ticker_payload(
        {
            "e": "bookTicker",
            "E": 1721044860456,
            "T": 1721044860457,
            "s": "BTCUSDT",
            "b": "65011.00",
            "B": "3.250",
            "a": "65010.00",
            "A": "1.750",
        }
    )

    with pytest.raises(ValidationError, match="bid_price"):
        map_book_ticker_payload(payload)
