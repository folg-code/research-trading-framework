"""Binance feed adapters for the local BTCUSDT dry-run runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol, final

from trading_framework.application.execution.local_btc_futures import (
    LocalBtcFuturesClosedBarFeedStepResult,
    LocalBtcFuturesDryRunConfig,
    LocalBtcFuturesDryRunRuntime,
    create_local_btc_futures_dry_run_runtime,
    run_local_btc_futures_closed_bar_feed_step,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.models import Heartbeat, RuntimeStatusSnapshot
from trading_framework.infrastructure.providers.binance.aiohttp_websocket import (
    AiohttpBinanceWebSocketConnector,
)
from trading_framework.infrastructure.providers.binance.futures_mapper import map_kline_payload
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    parse_combined_stream_payload,
    parse_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_streams import (
    BinanceFuturesStreamEndpoint,
    kline_1m_stream,
)
from trading_framework.infrastructure.providers.binance.futures_websocket import (
    BinanceFuturesWebSocketClient,
    BinanceFuturesWebSocketMessage,
    BinanceWebSocketConnector,
)
from trading_framework.market.models import MarketBar
from trading_framework.time.clocks.protocol import Clock


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesBinanceFeedState:
    """Local dry-run feed state accumulated from Binance market messages."""

    closed_bars: tuple[MarketBar, ...] = ()
    closed_bar_count: int = 0
    ignored_message_count: int = 0


@final
@dataclass(frozen=True, slots=True)
class LocalBtcFuturesBinanceMessageResult:
    """Result of applying one Binance message to the local dry-run runtime."""

    state: LocalBtcFuturesBinanceFeedState
    feed_step_result: LocalBtcFuturesClosedBarFeedStepResult | None = None
    ignored_reason: str | None = None

    @property
    def processed_closed_bar(self) -> bool:
        """Whether the message produced a closed-bar runtime step."""
        return self.feed_step_result is not None


class LocalBtcFuturesBinanceMessageClient(Protocol):
    """Minimal async client consumed by the local Binance dry-run loop."""

    async def receive(self) -> BinanceFuturesWebSocketMessage:
        """Receive one Binance WebSocket message."""
        ...

    async def close(self) -> None:
        """Close the message client."""
        ...


@final
@dataclass(frozen=True, slots=True)
class RunLocalBtcFuturesBinanceDryRunRequest:
    """Request for a bounded local BTCUSDT dry-run fed by Binance klines."""

    config: LocalBtcFuturesDryRunConfig
    duration_seconds: float
    heartbeat_seconds: float = 30.0
    max_closed_bars: int = 200
    max_messages: int | None = None

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            msg = "duration_seconds must be positive"
            raise ValidationError(msg)
        if self.heartbeat_seconds <= 0:
            msg = "heartbeat_seconds must be positive"
            raise ValidationError(msg)
        if self.max_closed_bars < 1:
            msg = "max_closed_bars must be positive"
            raise ValidationError(msg)
        if self.max_messages is not None and self.max_messages < 1:
            msg = "max_messages must be positive when provided"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class RunLocalBtcFuturesBinanceDryRunResult:
    """Result of a bounded local BTCUSDT dry-run fed by Binance klines."""

    runtime: LocalBtcFuturesDryRunRuntime
    feed_state: LocalBtcFuturesBinanceFeedState
    started_status: RuntimeStatusSnapshot
    heartbeat: Heartbeat
    stopped_status: RuntimeStatusSnapshot
    received_message_count: int


def handle_local_btc_futures_binance_message(
    runtime: LocalBtcFuturesDryRunRuntime,
    *,
    state: LocalBtcFuturesBinanceFeedState,
    message: BinanceFuturesWebSocketMessage,
    max_closed_bars: int = 200,
) -> LocalBtcFuturesBinanceMessageResult:
    """Apply one Binance market-data message to the local dry-run runtime."""
    if max_closed_bars < 1:
        msg = "max_closed_bars must be positive"
        raise ValidationError(msg)
    combined = parse_combined_stream_payload(message.payload)
    if "@kline_1m" not in combined.stream:
        return _ignored(state, "unsupported_stream")
    kline = parse_kline_payload(combined.data)
    if kline.symbol.strip().upper() != runtime.config.symbol:
        return _ignored(state, "symbol_mismatch")
    if not kline.is_closed:
        return _ignored(state, "open_kline")
    bar = map_kline_payload(kline)
    feed_step_result = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=state.closed_bars,
        bar=bar,
        max_closed_bars=max_closed_bars,
    )
    next_state = LocalBtcFuturesBinanceFeedState(
        closed_bars=feed_step_result.closed_bars,
        closed_bar_count=state.closed_bar_count + 1,
        ignored_message_count=state.ignored_message_count,
    )
    return LocalBtcFuturesBinanceMessageResult(
        state=next_state,
        feed_step_result=feed_step_result,
    )


async def run_local_btc_futures_binance_dry_run(
    request: RunLocalBtcFuturesBinanceDryRunRequest,
    *,
    clock: Clock | None = None,
    connector: BinanceWebSocketConnector | None = None,
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...] | None = None,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run a bounded local dry-run loop from Binance closed kline messages."""
    runtime = create_local_btc_futures_dry_run_runtime(
        request.config,
        clock=clock,
    )
    owned_connector: AiohttpBinanceWebSocketConnector | None = None
    if clients is None:
        if connector is None:
            owned_connector = AiohttpBinanceWebSocketConnector()
            connector = owned_connector
        clients = (
            BinanceFuturesWebSocketClient(
                symbol=runtime.config.symbol,
                endpoint=BinanceFuturesStreamEndpoint.MARKET,
                streams=(kline_1m_stream(runtime.config.symbol),),
                connector=connector,
            ),
        )

    started = runtime.session.start()
    heartbeat = runtime.session.record_heartbeat(message="local Binance dry-run runtime alive")
    try:
        loop_result = await _receive_binance_messages_until_bounded(
            runtime=runtime,
            request=request,
            clients=clients,
        )
        heartbeat = runtime.session.record_heartbeat(
            message="local Binance dry-run runtime stopping",
        )
        stopped = runtime.session.stop(message="bounded local Binance dry-run complete")
        return RunLocalBtcFuturesBinanceDryRunResult(
            runtime=runtime,
            feed_state=loop_result.state,
            started_status=started,
            heartbeat=heartbeat,
            stopped_status=stopped,
            received_message_count=loop_result.received_message_count,
        )
    finally:
        await asyncio.gather(*(client.close() for client in clients), return_exceptions=True)
        if owned_connector is not None:
            await owned_connector.close()


@final
@dataclass(frozen=True, slots=True)
class _ReceiveLoopResult:
    state: LocalBtcFuturesBinanceFeedState
    heartbeat: Heartbeat | None
    received_message_count: int


async def _receive_binance_messages_until_bounded(
    *,
    runtime: LocalBtcFuturesDryRunRuntime,
    request: RunLocalBtcFuturesBinanceDryRunRequest,
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...],
) -> _ReceiveLoopResult:
    if not clients:
        msg = "at least one Binance message client is required"
        raise ValidationError(msg)
    state = LocalBtcFuturesBinanceFeedState()
    heartbeat: Heartbeat | None = None
    received_message_count = 0
    loop = asyncio.get_running_loop()
    deadline = loop.time() + request.duration_seconds
    next_heartbeat_at = loop.time() + request.heartbeat_seconds
    pending: dict[asyncio.Task[BinanceFuturesWebSocketMessage], LocalBtcFuturesBinanceMessageClient]
    pending = {asyncio.create_task(client.receive()): client for client in clients}
    try:
        while pending:
            now = loop.time()
            if now >= deadline:
                break
            timeout = min(deadline - now, max(0.0, next_heartbeat_at - now))
            done, _ = await asyncio.wait(
                pending,
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                if loop.time() >= next_heartbeat_at:
                    heartbeat = runtime.session.record_heartbeat(
                        message="local Binance dry-run runtime alive",
                    )
                    next_heartbeat_at = loop.time() + request.heartbeat_seconds
                continue
            for task in done:
                client = pending.pop(task)
                message = task.result()
                result = handle_local_btc_futures_binance_message(
                    runtime,
                    state=state,
                    message=message,
                    max_closed_bars=request.max_closed_bars,
                )
                state = result.state
                received_message_count += 1
                if request.max_messages is None or received_message_count < request.max_messages:
                    pending[asyncio.create_task(client.receive())] = client
        return _ReceiveLoopResult(
            state=state,
            heartbeat=heartbeat,
            received_message_count=received_message_count,
        )
    finally:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending.keys(), return_exceptions=True)


def _ignored(
    state: LocalBtcFuturesBinanceFeedState,
    reason: str,
) -> LocalBtcFuturesBinanceMessageResult:
    return LocalBtcFuturesBinanceMessageResult(
        state=LocalBtcFuturesBinanceFeedState(
            closed_bars=state.closed_bars,
            closed_bar_count=state.closed_bar_count,
            ignored_message_count=state.ignored_message_count + 1,
        ),
        ignored_reason=reason,
    )
