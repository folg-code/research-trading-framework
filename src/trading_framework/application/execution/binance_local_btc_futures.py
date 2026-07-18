"""Binance feed adapters for the local BTCUSDT dry-run runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol, final

from trading_framework.application.execution.local_btc_futures import (
    LocalBtcFuturesClosedBarFeedStepResult,
    LocalBtcFuturesDryRunConfig,
    LocalBtcFuturesDryRunRuntime,
    create_local_btc_futures_dry_run_runtime,
    run_local_btc_futures_closed_bar_feed_step,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.execution import ExecutionStateRepository, PaperBrokerState
from trading_framework.execution.models import Heartbeat, RuntimeStatusSnapshot
from trading_framework.execution.models.market_data import (
    MarketFeedConnectionState,
    MarketFeedStatusSnapshot,
)
from trading_framework.execution.runtime.health_policy import resolve_runtime_health
from trading_framework.infrastructure.providers.binance.aiohttp_websocket import (
    AiohttpBinanceWebSocketConnector,
)
from trading_framework.infrastructure.providers.binance.futures_mapper import map_kline_payload
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    parse_combined_stream_payload,
    parse_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_rest import (
    BinanceFuturesRestError,
    fetch_closed_klines,
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


class LocalBtcFuturesBinanceTelemetrySink(Protocol):
    """Optional observer for local Binance dry-run lifecycle telemetry."""

    def runtime_started(
        self,
        config: LocalBtcFuturesDryRunConfig,
        status: RuntimeStatusSnapshot,
    ) -> None:
        """Record that the runtime started."""
        ...

    def heartbeat_recorded(
        self,
        config: LocalBtcFuturesDryRunConfig,
        heartbeat: Heartbeat,
    ) -> None:
        """Record a runtime heartbeat."""
        ...

    def market_message_processed(
        self,
        config: LocalBtcFuturesDryRunConfig,
        result: LocalBtcFuturesBinanceMessageResult,
        *,
        received_message_count: int,
    ) -> None:
        """Record one processed or ignored market-data message."""
        ...

    def runtime_stopped(
        self,
        config: LocalBtcFuturesDryRunConfig,
        status: RuntimeStatusSnapshot,
    ) -> None:
        """Record that the runtime stopped."""
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
    max_closed_bars: int | None = None,
) -> LocalBtcFuturesBinanceMessageResult:
    """Apply one Binance market-data message to the local dry-run runtime."""
    window = max_closed_bars if max_closed_bars is not None else runtime.max_closed_bars
    if window < 1:
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
        max_closed_bars=window,
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
    state_repository: ExecutionStateRepository | None = None,
    telemetry: LocalBtcFuturesBinanceTelemetrySink | None = None,
    connector: BinanceWebSocketConnector | None = None,
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...] | None = None,
) -> RunLocalBtcFuturesBinanceDryRunResult:
    """Run a bounded local dry-run loop from Binance closed kline messages."""
    runtime = create_local_btc_futures_dry_run_runtime(
        request.config,
        clock=clock,
        state_repository=state_repository,
        max_closed_bars=request.max_closed_bars,
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
    _persist_status(runtime, started)
    _persist_broker_state(runtime, runtime.initial_state)
    if telemetry is not None:
        telemetry.runtime_started(runtime.config, started)
    heartbeat = _record_feed_aware_heartbeat(
        runtime,
        clients=clients,
        heartbeat_seconds=request.heartbeat_seconds,
        message="local Binance dry-run runtime alive",
    )
    if telemetry is not None:
        telemetry.heartbeat_recorded(runtime.config, heartbeat)
    feed_state = LocalBtcFuturesBinanceFeedState()
    received_message_count = 0
    try:
        loop_result = await _receive_binance_messages_until_bounded(
            runtime=runtime,
            request=request,
            clients=clients,
            telemetry=telemetry,
        )
        feed_state = loop_result.state
        received_message_count = loop_result.received_message_count
        heartbeat = _record_feed_aware_heartbeat(
            runtime,
            clients=clients,
            heartbeat_seconds=request.heartbeat_seconds,
            message="local Binance dry-run runtime stopping",
        )
        if telemetry is not None:
            telemetry.heartbeat_recorded(runtime.config, heartbeat)
        stopped = runtime.session.stop(message="bounded local Binance dry-run complete")
        _persist_status(runtime, stopped)
        if telemetry is not None:
            telemetry.runtime_stopped(runtime.config, stopped)
        return RunLocalBtcFuturesBinanceDryRunResult(
            runtime=runtime,
            feed_state=feed_state,
            started_status=started,
            heartbeat=heartbeat,
            stopped_status=stopped,
            received_message_count=received_message_count,
        )
    except asyncio.CancelledError:
        stopped = runtime.session.stop(message="runtime interrupted by signal")
        _persist_status(runtime, stopped)
        if telemetry is not None:
            telemetry.runtime_stopped(runtime.config, stopped)
        return RunLocalBtcFuturesBinanceDryRunResult(
            runtime=runtime,
            feed_state=feed_state,
            started_status=started,
            heartbeat=heartbeat,
            stopped_status=stopped,
            received_message_count=received_message_count,
        )
    except Exception as exc:
        failed = runtime.session.fail(message=str(exc)[:500] or "runtime failed")
        _persist_status(runtime, failed)
        if telemetry is not None:
            telemetry.runtime_stopped(runtime.config, failed)
        raise
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
    telemetry: LocalBtcFuturesBinanceTelemetrySink | None = None,
) -> _ReceiveLoopResult:
    if not clients:
        msg = "at least one Binance message client is required"
        raise ValidationError(msg)
    state = _bootstrap_feed_state(runtime)
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
                    heartbeat = _record_feed_aware_heartbeat(
                        runtime,
                        clients=clients,
                        heartbeat_seconds=request.heartbeat_seconds,
                        message="local Binance dry-run runtime alive",
                    )
                    if telemetry is not None:
                        telemetry.heartbeat_recorded(runtime.config, heartbeat)
                    next_heartbeat_at = loop.time() + request.heartbeat_seconds
                continue
            for task in done:
                client = pending.pop(task)
                message = task.result()
                result = handle_local_btc_futures_binance_message(
                    runtime,
                    state=state,
                    message=message,
                    max_closed_bars=runtime.max_closed_bars,
                )
                state = result.state
                received_message_count += 1
                if telemetry is not None:
                    telemetry.market_message_processed(
                        runtime.config,
                        result,
                        received_message_count=received_message_count,
                    )
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


def _bootstrap_feed_state(runtime: LocalBtcFuturesDryRunRuntime) -> LocalBtcFuturesBinanceFeedState:
    """Seed the closed-bar buffer from Binance REST; fall back to empty on failure."""
    try:
        bars = fetch_closed_klines(
            symbol=runtime.config.symbol,
            limit=runtime.required_closed_bars,
        )
    except (BinanceFuturesRestError, ValidationError, TypeError, ValueError):
        return LocalBtcFuturesBinanceFeedState()
    if len(bars) < runtime.required_closed_bars:
        return LocalBtcFuturesBinanceFeedState(
            closed_bars=bars,
            closed_bar_count=len(bars),
        )
    return LocalBtcFuturesBinanceFeedState(
        closed_bars=bars,
        closed_bar_count=len(bars),
    )


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


def _record_feed_aware_heartbeat(
    runtime: LocalBtcFuturesDryRunRuntime,
    *,
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...],
    heartbeat_seconds: float,
    message: str,
) -> Heartbeat:
    """Emit a heartbeat whose RuntimeHealth reflects market-feed freshness."""
    latest = runtime.session.latest_status(runtime.config.runtime_id)
    last_market_event_at = None if latest is None else latest.last_market_event_at
    feed = _primary_feed_snapshot(clients)
    degraded_after = timedelta(seconds=max(heartbeat_seconds * 3.0, 1.0))
    stale_after = timedelta(seconds=max(heartbeat_seconds * 6.0, 2.0))
    health = resolve_runtime_health(
        now=runtime.session.clock.now(),
        last_market_event_at=last_market_event_at,
        feed_connection=None if feed is None else feed.state,
        degraded_after=degraded_after,
        stale_after=stale_after,
    )
    heartbeat = runtime.session.record_heartbeat(
        status=health,
        message=message,
        feed=feed,
    )
    _persist_latest_status(runtime)
    return heartbeat


def _primary_feed_snapshot(
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...],
) -> MarketFeedStatusSnapshot | None:
    """Return the worst feed status among clients that expose status_snapshot."""
    priority = {
        MarketFeedConnectionState.FAILED: 4,
        MarketFeedConnectionState.RECONNECTING: 3,
        MarketFeedConnectionState.CONNECTING: 2,
        MarketFeedConnectionState.CONNECTED: 1,
        MarketFeedConnectionState.STOPPED: 0,
    }
    worst: MarketFeedStatusSnapshot | None = None
    worst_score = -1
    for client in clients:
        status_snapshot = getattr(client, "status_snapshot", None)
        if not callable(status_snapshot):
            continue
        snapshot = status_snapshot()
        if not isinstance(snapshot, MarketFeedStatusSnapshot):
            continue
        score = priority.get(snapshot.state, 0)
        if score > worst_score:
            worst = snapshot
            worst_score = score
    return worst


def _worst_feed_connection(
    clients: tuple[LocalBtcFuturesBinanceMessageClient, ...],
) -> MarketFeedConnectionState | None:
    """Return the worst connection state among clients that expose status_snapshot."""
    snapshot = _primary_feed_snapshot(clients)
    return None if snapshot is None else snapshot.state


def _persist_status(
    runtime: LocalBtcFuturesDryRunRuntime,
    status: RuntimeStatusSnapshot,
) -> None:
    runtime.state_repository.save_runtime_status(status)


def _persist_latest_status(runtime: LocalBtcFuturesDryRunRuntime) -> None:
    status = runtime.session.latest_status(runtime.config.runtime_id)
    if status is not None:
        _persist_status(runtime, status)


def _persist_broker_state(
    runtime: LocalBtcFuturesDryRunRuntime,
    state: PaperBrokerState,
) -> None:
    runtime.state_repository.save_account(runtime.config.runtime_id, state.account)
    runtime.state_repository.save_position(runtime.config.runtime_id, state.position)
