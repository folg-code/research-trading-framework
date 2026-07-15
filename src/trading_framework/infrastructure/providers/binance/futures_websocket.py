"""Transport-agnostic Binance USD-M futures WebSocket client."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, final

from trading_framework.core.exceptions import TradingFrameworkError
from trading_framework.execution.models import (
    MarketFeedConnectionState,
    MarketFeedStatusSnapshot,
)
from trading_framework.infrastructure.providers.binance.futures_reconnect import (
    DEFAULT_RECONNECT_BACKOFF_POLICY,
    ReconnectBackoffPolicy,
)
from trading_framework.infrastructure.providers.binance.futures_streams import (
    BinanceFuturesStream,
    BinanceFuturesStreamEndpoint,
    build_combined_stream_url,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

AsyncSleep = Callable[[float], Awaitable[None]]


class BinanceWebSocketConnection(Protocol):
    """Minimal async WebSocket connection required by the Binance feed client."""

    async def receive_json(self) -> object:
        """Receive one decoded JSON payload from the socket."""
        ...

    async def close(self) -> None:
        """Close the underlying socket."""
        ...


class BinanceWebSocketConnector(Protocol):
    """Open a WebSocket connection for a URL."""

    async def connect(self, url: str) -> BinanceWebSocketConnection:
        """Connect to a WebSocket URL."""
        ...


class BinanceFuturesWebSocketClientError(TradingFrameworkError):
    """Raised when the Binance WebSocket client exhausts reconnect attempts."""


@final
@dataclass(frozen=True, slots=True)
class BinanceFuturesWebSocketMessage:
    """One decoded Binance WebSocket message with endpoint context."""

    endpoint: BinanceFuturesStreamEndpoint
    url: str
    payload: object


@final
@dataclass(slots=True)
class BinanceFuturesWebSocketClient:
    """Receive Binance USD-M futures stream payloads with bounded reconnect."""

    symbol: str
    endpoint: BinanceFuturesStreamEndpoint
    streams: tuple[BinanceFuturesStream, ...]
    connector: BinanceWebSocketConnector
    clock: Clock = field(default_factory=SystemClock)
    backoff_policy: ReconnectBackoffPolicy = DEFAULT_RECONNECT_BACKOFF_POLICY
    sleep: AsyncSleep = asyncio.sleep
    provider: str = "binance_usdm"

    _connection: BinanceWebSocketConnection | None = field(default=None, init=False)
    _state: MarketFeedConnectionState = field(
        default=MarketFeedConnectionState.STOPPED,
        init=False,
    )
    _last_message_at: datetime | None = field(default=None, init=False)
    _reconnect_count: int = field(default=0, init=False)
    _last_error: str | None = field(default=None, init=False)

    @property
    def url(self) -> str:
        """Return the routed combined stream URL."""
        return build_combined_stream_url(self.endpoint, self.streams)

    def status_snapshot(self) -> MarketFeedStatusSnapshot:
        """Return the current provider-independent feed status snapshot."""
        return MarketFeedStatusSnapshot(
            provider=self.provider,
            symbol=self.symbol,
            state=self._state,
            recorded_at=self.clock.now(),
            last_message_at=self._last_message_at,
            reconnect_count=self._reconnect_count,
            last_error=self._last_error,
        )

    async def receive(self) -> BinanceFuturesWebSocketMessage:
        """Receive one decoded JSON message, reconnecting within the configured policy."""
        while True:
            if self._connection is None:
                try:
                    await self._connect()
                except Exception as exc:
                    await self._schedule_reconnect(exc)
                    continue
            connection = self._connection
            if connection is None:
                continue

            try:
                payload = await connection.receive_json()
            except Exception as exc:
                await self._schedule_reconnect(exc)
                continue

            self._state = MarketFeedConnectionState.CONNECTED
            self._last_error = None
            self._last_message_at = self.clock.now()
            return BinanceFuturesWebSocketMessage(
                endpoint=self.endpoint,
                url=self.url,
                payload=payload,
            )

    async def close(self) -> None:
        """Close the active connection and mark the feed as stopped."""
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()
        self._state = MarketFeedConnectionState.STOPPED

    async def _connect(self) -> None:
        if self._reconnect_count:
            self._state = MarketFeedConnectionState.RECONNECTING
        else:
            self._state = MarketFeedConnectionState.CONNECTING
        self._connection = await self.connector.connect(self.url)
        self._state = MarketFeedConnectionState.CONNECTED
        self._last_error = None

    async def _schedule_reconnect(self, exc: Exception) -> None:
        await self._close_connection()
        if self._reconnect_count >= self.backoff_policy.max_attempts:
            self._state = MarketFeedConnectionState.FAILED
            self._last_error = str(exc)
            msg = "Binance futures WebSocket reconnect attempts exhausted"
            raise BinanceFuturesWebSocketClientError(msg) from exc

        delay = self.backoff_policy.delay_for_attempt(self._reconnect_count)
        self._reconnect_count += 1
        self._state = MarketFeedConnectionState.RECONNECTING
        self._last_error = str(exc)
        await self.sleep(delay.total_seconds())

    async def _close_connection(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            await connection.close()
