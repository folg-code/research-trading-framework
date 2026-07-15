"""Local smoke runner for Binance USD-M futures live market data."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance.aiohttp_websocket import (
    AiohttpBinanceWebSocketConnector,
)
from trading_framework.infrastructure.providers.binance.futures_mapper import (
    map_book_ticker_payload,
    map_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    parse_book_ticker_payload,
    parse_combined_stream_payload,
    parse_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_streams import (
    BinanceFuturesStream,
    book_ticker_stream,
    group_streams_by_endpoint,
    kline_1m_stream,
)
from trading_framework.infrastructure.providers.binance.futures_websocket import (
    BinanceFuturesWebSocketClient,
    BinanceFuturesWebSocketMessage,
)

SmokeWriter = Callable[[dict[str, object]], None]


@final
@dataclass(frozen=True, slots=True)
class BinanceFuturesSmokeConfig:
    """Configuration for a bounded Binance futures feed smoke run."""

    symbol: str = "BTCUSDT"
    duration_seconds: float = 10.0
    max_messages: int = 20

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            msg = "symbol must be non-empty"
            raise ValidationError(msg)
        if self.duration_seconds <= 0:
            msg = "duration_seconds must be positive"
            raise ValidationError(msg)
        if self.max_messages < 1:
            msg = "max_messages must be positive"
            raise ValidationError(msg)
        object.__setattr__(self, "symbol", symbol)

    def streams(self) -> tuple[BinanceFuturesStream, ...]:
        """Return the stream set for this smoke run."""
        return (
            kline_1m_stream(self.symbol),
            book_ticker_stream(self.symbol),
        )


async def run_binance_futures_feed_smoke(
    config: BinanceFuturesSmokeConfig,
    writer: SmokeWriter,
) -> int:
    """Run a bounded live Binance futures feed smoke test."""
    connector = AiohttpBinanceWebSocketConnector()
    clients = _build_clients(config, connector)
    try:
        return await _receive_until_limit(clients, config, writer)
    finally:
        await asyncio.gather(*(client.close() for client in clients), return_exceptions=True)
        await connector.close()


def normalize_smoke_message(message: BinanceFuturesWebSocketMessage) -> dict[str, object] | None:
    """Normalize a received Binance message into a smoke JSON payload."""
    combined = parse_combined_stream_payload(message.payload)
    if "@bookTicker" in combined.stream:
        snapshot = map_book_ticker_payload(parse_book_ticker_payload(combined.data))
        return {
            "event": "book_ticker",
            "endpoint": message.endpoint.value,
            "stream": combined.stream,
            "symbol": snapshot.symbol,
            "bid_price": str(snapshot.bid_price.value),
            "ask_price": str(snapshot.ask_price.value),
            "event_at": snapshot.event_at.isoformat(),
            "received_at": _optional_isoformat(snapshot.received_at),
        }
    if "@kline_1m" in combined.stream:
        kline = parse_kline_payload(combined.data)
        if not kline.is_closed:
            return None
        bar = map_kline_payload(kline)
        return {
            "event": "closed_kline_1m",
            "endpoint": message.endpoint.value,
            "stream": combined.stream,
            "symbol": kline.symbol,
            "open": str(bar.open.value),
            "high": str(bar.high.value),
            "low": str(bar.low.value),
            "close": str(bar.close.value),
            "volume": str(Decimal(bar.volume.value)),
            "observed_at": bar.observed_at.isoformat(),
            "available_at": bar.available_at.isoformat(),
        }
    return None


def _build_clients(
    config: BinanceFuturesSmokeConfig,
    connector: AiohttpBinanceWebSocketConnector,
) -> tuple[BinanceFuturesWebSocketClient, ...]:
    grouped_streams = group_streams_by_endpoint(config.streams())
    return tuple(
        BinanceFuturesWebSocketClient(
            symbol=config.symbol,
            endpoint=endpoint,
            streams=streams,
            connector=connector,
        )
        for endpoint, streams in grouped_streams.items()
    )


async def _receive_until_limit(
    clients: tuple[BinanceFuturesWebSocketClient, ...],
    config: BinanceFuturesSmokeConfig,
    writer: SmokeWriter,
) -> int:
    emitted = 0
    deadline = asyncio.get_running_loop().time() + config.duration_seconds
    pending: dict[asyncio.Task[BinanceFuturesWebSocketMessage], BinanceFuturesWebSocketClient] = {
        asyncio.create_task(client.receive()): client for client in clients
    }
    try:
        while pending and emitted < config.max_messages:
            timeout = deadline - asyncio.get_running_loop().time()
            if timeout <= 0:
                break
            done, _ = await asyncio.wait(
                pending,
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                break
            for task in done:
                client = pending.pop(task)
                payload = normalize_smoke_message(task.result())
                if payload is not None:
                    writer(payload)
                    emitted += 1
                if emitted < config.max_messages:
                    pending[asyncio.create_task(client.receive())] = client
        return emitted
    finally:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending.keys(), return_exceptions=True)


def _optional_isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
