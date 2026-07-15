"""Tests for the aiohttp Binance WebSocket transport adapter."""

import asyncio
from types import SimpleNamespace
from typing import cast

import aiohttp
import pytest

from trading_framework.infrastructure.providers.binance import (
    AiohttpBinanceWebSocketConnection,
    AiohttpBinanceWebSocketConnector,
    AiohttpBinanceWebSocketError,
)


class FakeSocket:
    def __init__(self, message: object) -> None:
        self._message = message
        self.closed = False

    async def receive(self) -> object:
        return self._message

    async def close(self) -> None:
        self.closed = True

    def exception(self) -> BaseException | None:
        return RuntimeError("socket error")


class FakeSession:
    def __init__(self, socket: FakeSocket) -> None:
        self.socket = socket
        self.urls: list[str] = []
        self.closed = False

    async def ws_connect(
        self,
        url: str,
        *,
        autoping: bool,
        heartbeat: float,
    ) -> FakeSocket:
        self.urls.append(url)
        assert autoping
        assert heartbeat == 180.0
        return self.socket

    async def close(self) -> None:
        self.closed = True


def _message(message_type: aiohttp.WSMsgType, data: object = "") -> object:
    return SimpleNamespace(type=message_type, data=data)


def test_aiohttp_connection_decodes_text_json_payload() -> None:
    async def run() -> None:
        socket = FakeSocket(_message(aiohttp.WSMsgType.TEXT, '{"stream":"btcusdt@kline_1m"}'))
        connection = AiohttpBinanceWebSocketConnection(
            socket=cast(aiohttp.ClientWebSocketResponse, socket)
        )

        payload = await connection.receive_json()

        assert payload == {"stream": "btcusdt@kline_1m"}

    asyncio.run(run())


def test_aiohttp_connection_decodes_binary_json_payload() -> None:
    async def run() -> None:
        socket = FakeSocket(_message(aiohttp.WSMsgType.BINARY, b'{"stream":"btcusdt@bookTicker"}'))
        connection = AiohttpBinanceWebSocketConnection(
            socket=cast(aiohttp.ClientWebSocketResponse, socket)
        )

        payload = await connection.receive_json()

        assert payload == {"stream": "btcusdt@bookTicker"}

    asyncio.run(run())


def test_aiohttp_connection_raises_on_closed_socket_message() -> None:
    async def run() -> None:
        socket = FakeSocket(_message(aiohttp.WSMsgType.CLOSED))
        connection = AiohttpBinanceWebSocketConnection(
            socket=cast(aiohttp.ClientWebSocketResponse, socket)
        )

        with pytest.raises(AiohttpBinanceWebSocketError, match="closed"):
            await connection.receive_json()

    asyncio.run(run())


def test_aiohttp_connector_uses_supplied_session_and_returns_connection() -> None:
    async def run() -> None:
        socket = FakeSocket(_message(aiohttp.WSMsgType.TEXT, "{}"))
        session = FakeSession(socket)
        connector = AiohttpBinanceWebSocketConnector(session=cast(aiohttp.ClientSession, session))

        connection = await connector.connect("wss://example.test/ws")
        payload = await connection.receive_json()
        await connection.close()
        await connector.close()

        assert payload == {}
        assert session.urls == ["wss://example.test/ws"]
        assert socket.closed
        assert not session.closed

    asyncio.run(run())
