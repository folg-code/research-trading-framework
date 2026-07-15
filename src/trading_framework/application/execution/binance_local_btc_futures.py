"""Binance feed adapters for the local BTCUSDT dry-run runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final

from trading_framework.application.execution.local_btc_futures import (
    LocalBtcFuturesClosedBarFeedStepResult,
    LocalBtcFuturesDryRunRuntime,
    run_local_btc_futures_closed_bar_feed_step,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance.futures_mapper import map_kline_payload
from trading_framework.infrastructure.providers.binance.futures_payloads import (
    parse_combined_stream_payload,
    parse_kline_payload,
)
from trading_framework.infrastructure.providers.binance.futures_websocket import (
    BinanceFuturesWebSocketMessage,
)
from trading_framework.market.models import MarketBar


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
