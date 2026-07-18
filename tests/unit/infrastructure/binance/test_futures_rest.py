"""Tests for Binance USD-M REST closed-klines bootstrap helper."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request

import pytest

from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesRestError,
    fetch_closed_klines,
)


class _FakeResponse:
    def __init__(self, payload: list[list[Any]]) -> None:
        self._body = json.dumps(payload).encode("utf-8")
        self.status = 200

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _row(open_ms: int, close: str) -> list[Any]:
    return [
        open_ms,
        close,
        close,
        close,
        close,
        "1.0",
        open_ms + 59_999,
        "0",
        0,
        "0",
        "0",
        "0",
    ]


def test_fetch_closed_klines_drops_newest_open_candidate() -> None:
    rows = [
        _row(1_000, "100"),
        _row(61_000, "101"),
        _row(121_000, "102"),
        _row(181_000, "999"),  # dropped as newest / potentially open
    ]
    calls: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        calls.append(request)
        assert timeout == 5.0
        assert "limit=4" in request.full_url  # limit+1
        return _FakeResponse(rows)

    bars = fetch_closed_klines(
        symbol="btcusdt",
        limit=3,
        timeout_seconds=5.0,
        urlopen=fake_urlopen,
    )

    assert len(bars) == 3
    assert [float(bar.close.value) for bar in bars] == [100.0, 101.0, 102.0]
    assert len(calls) == 1


def test_fetch_closed_klines_maps_network_errors() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        del request, timeout
        raise URLError("timed out")

    with pytest.raises(BinanceFuturesRestError, match="unreachable"):
        fetch_closed_klines(symbol="BTCUSDT", limit=2, urlopen=fake_urlopen)
