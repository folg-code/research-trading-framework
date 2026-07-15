"""Tests for the Binance futures WebSocket client wrapper."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trading_framework.execution import MarketFeedConnectionState
from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesWebSocketClient,
    BinanceFuturesWebSocketClientError,
    ReconnectBackoffPolicy,
    kline_1m_stream,
)


class AdvancingClock:
    def __init__(self) -> None:
        self._times = [
            datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC),
            datetime(2026, 7, 15, 12, 0, 1, tzinfo=UTC),
            datetime(2026, 7, 15, 12, 0, 2, tzinfo=UTC),
            datetime(2026, 7, 15, 12, 0, 3, tzinfo=UTC),
        ]

    def now(self) -> datetime:
        if len(self._times) == 1:
            return self._times[0]
        return self._times.pop(0)


class FakeConnection:
    def __init__(self, messages: list[object], *, fail_first: bool = False) -> None:
        self._messages = messages
        self._fail_first = fail_first
        self.closed = False

    async def receive_json(self) -> object:
        if self._fail_first:
            self._fail_first = False
            raise RuntimeError("socket closed")
        return self._messages.pop(0)

    async def close(self) -> None:
        self.closed = True


class FakeConnector:
    def __init__(self, connections: list[FakeConnection]) -> None:
        self.connections = connections
        self.urls: list[str] = []

    async def connect(self, url: str) -> FakeConnection:
        self.urls.append(url)
        return self.connections.pop(0)


async def _noop_sleep(_seconds: float) -> None:
    return None


def test_websocket_client_receives_one_decoded_message_and_updates_status() -> None:
    async def run() -> None:
        payload = {"e": "kline", "s": "BTCUSDT"}
        connector = FakeConnector([FakeConnection([payload])])
        client = BinanceFuturesWebSocketClient(
            symbol="BTCUSDT",
            endpoint=kline_1m_stream("BTCUSDT").endpoint,
            streams=(kline_1m_stream("BTCUSDT"),),
            connector=connector,
            clock=AdvancingClock(),
            sleep=_noop_sleep,
        )

        message = await client.receive()
        status = client.status_snapshot()

        assert message.payload == payload
        assert message.url == "wss://fstream.binance.com/market/stream?streams=btcusdt@kline_1m"
        assert connector.urls == [message.url]
        assert status.state is MarketFeedConnectionState.CONNECTED
        assert status.last_message_at == datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)
        assert status.reconnect_count == 0

    asyncio.run(run())


def test_websocket_client_reconnects_after_receive_error() -> None:
    async def run() -> None:
        payload = {"e": "kline", "s": "BTCUSDT"}
        sleeps: list[float] = []

        async def record_sleep(seconds: float) -> None:
            sleeps.append(seconds)

        first = FakeConnection([], fail_first=True)
        second = FakeConnection([payload])
        connector = FakeConnector([first, second])
        client = BinanceFuturesWebSocketClient(
            symbol="BTCUSDT",
            endpoint=kline_1m_stream("BTCUSDT").endpoint,
            streams=(kline_1m_stream("BTCUSDT"),),
            connector=connector,
            clock=AdvancingClock(),
            backoff_policy=ReconnectBackoffPolicy(
                initial_delay=datetime.resolution,
                multiplier=Decimal("1"),
                max_attempts=2,
            ),
            sleep=record_sleep,
        )

        message = await client.receive()
        status = client.status_snapshot()

        assert message.payload == payload
        assert first.closed
        assert len(connector.urls) == 2
        assert sleeps == [datetime.resolution.total_seconds()]
        assert status.state is MarketFeedConnectionState.CONNECTED
        assert status.reconnect_count == 1
        assert status.last_error is None

    asyncio.run(run())


def test_websocket_client_marks_failed_when_reconnect_attempts_are_exhausted() -> None:
    async def run() -> None:
        connector = FakeConnector(
            [
                FakeConnection([], fail_first=True),
                FakeConnection([], fail_first=True),
            ]
        )
        client = BinanceFuturesWebSocketClient(
            symbol="BTCUSDT",
            endpoint=kline_1m_stream("BTCUSDT").endpoint,
            streams=(kline_1m_stream("BTCUSDT"),),
            connector=connector,
            clock=AdvancingClock(),
            backoff_policy=ReconnectBackoffPolicy(
                initial_delay=datetime.resolution,
                multiplier=Decimal("1"),
                max_attempts=1,
            ),
            sleep=_noop_sleep,
        )

        with pytest.raises(BinanceFuturesWebSocketClientError, match="exhausted"):
            await client.receive()

        status = client.status_snapshot()
        assert status.state is MarketFeedConnectionState.FAILED
        assert status.reconnect_count == 1
        assert status.last_error == "socket closed"

    asyncio.run(run())
