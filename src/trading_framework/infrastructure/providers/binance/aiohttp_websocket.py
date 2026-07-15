"""aiohttp transport adapter for Binance USD-M futures WebSocket feeds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import final

import aiohttp

from trading_framework.core.exceptions import TradingFrameworkError


class AiohttpBinanceWebSocketError(TradingFrameworkError):
    """Raised when the aiohttp WebSocket transport cannot provide JSON payloads."""


@final
@dataclass(frozen=True, slots=True)
class AiohttpBinanceWebSocketConnection:
    """Adapt an aiohttp WebSocket response to the Binance connector protocol."""

    socket: aiohttp.ClientWebSocketResponse

    async def receive_json(self) -> object:
        """Receive one JSON payload from the WebSocket."""
        message = await self.socket.receive()
        if message.type is aiohttp.WSMsgType.TEXT:
            return json.loads(message.data)
        if message.type is aiohttp.WSMsgType.BINARY:
            return json.loads(message.data.decode("utf-8"))
        if message.type in {
            aiohttp.WSMsgType.CLOSE,
            aiohttp.WSMsgType.CLOSED,
            aiohttp.WSMsgType.CLOSING,
        }:
            msg = "Binance WebSocket closed"
            raise AiohttpBinanceWebSocketError(msg)
        if message.type is aiohttp.WSMsgType.ERROR:
            error = self.socket.exception()
            msg = "Binance WebSocket received an error message"
            raise AiohttpBinanceWebSocketError(msg) from error

        msg = f"unsupported Binance WebSocket message type: {message.type!s}"
        raise AiohttpBinanceWebSocketError(msg)

    async def close(self) -> None:
        """Close the WebSocket response."""
        await self.socket.close()


@final
@dataclass(slots=True)
class AiohttpBinanceWebSocketConnector:
    """Open Binance WebSocket connections through aiohttp."""

    session: aiohttp.ClientSession | None = None
    heartbeat_seconds: float = 180.0

    _owned_session: aiohttp.ClientSession | None = None

    async def connect(self, url: str) -> AiohttpBinanceWebSocketConnection:
        """Open a WebSocket connection for the given URL."""
        session = self.session
        if session is None:
            session = aiohttp.ClientSession()
            self._owned_session = session
        socket = await session.ws_connect(
            url,
            autoping=True,
            heartbeat=self.heartbeat_seconds,
        )
        return AiohttpBinanceWebSocketConnection(socket=socket)

    async def close(self) -> None:
        """Close a session owned by this connector."""
        session = self._owned_session
        self._owned_session = None
        if session is not None:
            await session.close()
