"""Tests for Binance message handling in the local BTC futures dry-run runtime."""

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from trading_framework.application.execution import (
    LocalBtcFuturesBinanceFeedState,
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesBinanceDryRunRequest,
    create_local_btc_futures_dry_run_runtime,
    handle_local_btc_futures_binance_message,
    run_local_btc_futures_binance_dry_run,
)
from trading_framework.execution import ExecutionReadModelQuery
from trading_framework.execution.models import Heartbeat, RuntimeStatusSnapshot
from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesStreamEndpoint,
    BinanceFuturesWebSocketMessage,
)
from trading_framework.infrastructure.storage.execution_events import read_jsonl_execution_events
from trading_framework.strategy import BtcFuturesDemoStrategyConfig
from trading_framework.time.clocks.fixed import FixedClock

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "binance"
NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class FakeBinanceMessageClient:
    messages: list[BinanceFuturesWebSocketMessage]
    closed: bool = False

    async def receive(self) -> BinanceFuturesWebSocketMessage:
        if not self.messages:
            await asyncio.sleep(3600)
            raise AssertionError("fake Binance client exhausted")
        return self.messages.pop(0)

    async def close(self) -> None:
        self.closed = True


@dataclass(slots=True)
class FakeTelemetry:
    started: list[RuntimeStatusSnapshot]
    heartbeats: list[Heartbeat]
    messages: list[int]
    stopped: list[RuntimeStatusSnapshot]

    def runtime_started(
        self,
        config: LocalBtcFuturesDryRunConfig,
        status: RuntimeStatusSnapshot,
    ) -> None:
        self.started.append(status)

    def heartbeat_recorded(
        self,
        config: LocalBtcFuturesDryRunConfig,
        heartbeat: Heartbeat,
    ) -> None:
        self.heartbeats.append(heartbeat)

    def market_message_processed(
        self,
        config: LocalBtcFuturesDryRunConfig,
        result: object,
        *,
        received_message_count: int,
    ) -> None:
        self.messages.append(received_message_count)

    def runtime_stopped(
        self,
        config: LocalBtcFuturesDryRunConfig,
        status: RuntimeStatusSnapshot,
    ) -> None:
        self.stopped.append(status)


def _load_fixture(name: str) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8")),
    )


def _message(payload: object, stream: str = "btcusdt@kline_1m") -> BinanceFuturesWebSocketMessage:
    wrapped_payload = payload
    if not isinstance(payload, dict) or "stream" not in payload or "data" not in payload:
        wrapped_payload = {"stream": stream, "data": payload}
    return BinanceFuturesWebSocketMessage(
        endpoint=BinanceFuturesStreamEndpoint.MARKET,
        url=f"wss://fstream.binance.com/market/stream?streams={stream}",
        payload=wrapped_payload,
    )


def test_binance_closed_kline_message_runs_local_dry_run_step(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            strategy_config=BtcFuturesDemoStrategyConfig(ema_period=2),
        ),
        clock=FixedClock(NOW),
    )

    result = handle_local_btc_futures_binance_message(
        runtime,
        state=LocalBtcFuturesBinanceFeedState(),
        message=_message(_load_fixture("usdm_kline_1m_closed.json")),
        max_closed_bars=3,
    )

    assert result.processed_closed_bar
    assert result.feed_step_result is not None
    assert result.state.closed_bar_count == 1
    assert result.state.ignored_message_count == 0
    assert len(result.state.closed_bars) == 1
    assert result.state.closed_bars[0].close.value == Decimal("65010.50")
    assert result.feed_step_result.step_result.signal_evaluation.close == 65010.5
    event_rows = read_jsonl_execution_events(tmp_path / "events.jsonl")
    assert [row["event_type"] for row in event_rows] == ["market_event_received"]


def test_binance_open_kline_message_is_ignored(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl"),
        clock=FixedClock(NOW),
    )

    result = handle_local_btc_futures_binance_message(
        runtime,
        state=LocalBtcFuturesBinanceFeedState(),
        message=_message(_load_fixture("usdm_kline_1m_open.json")),
    )

    assert not result.processed_closed_bar
    assert result.ignored_reason == "open_kline"
    assert result.state.closed_bar_count == 0
    assert result.state.ignored_message_count == 1


def test_binance_non_matching_message_is_ignored(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl"),
        clock=FixedClock(NOW),
    )

    unsupported = handle_local_btc_futures_binance_message(
        runtime,
        state=LocalBtcFuturesBinanceFeedState(),
        message=_message(_load_fixture("usdm_book_ticker.json"), stream="btcusdt@bookTicker"),
    )
    wrong_symbol_payload = _load_fixture("usdm_kline_1m_closed.json")
    wrong_symbol_payload["stream"] = "ethusdt@kline_1m"
    data = cast(dict[str, object], wrong_symbol_payload["data"])
    data["s"] = "ETHUSDT"
    wrong_symbol = handle_local_btc_futures_binance_message(
        runtime,
        state=unsupported.state,
        message=_message(wrong_symbol_payload),
    )

    assert unsupported.ignored_reason == "unsupported_stream"
    assert wrong_symbol.ignored_reason == "symbol_mismatch"
    assert wrong_symbol.state.closed_bar_count == 0
    assert wrong_symbol.state.ignored_message_count == 2


def test_binance_dry_run_loop_processes_bounded_fake_messages(tmp_path: Path) -> None:
    telemetry = FakeTelemetry(started=[], heartbeats=[], messages=[], stopped=[])
    client = FakeBinanceMessageClient(
        messages=[
            _message(_load_fixture("usdm_kline_1m_closed.json")),
            _message(_load_fixture("usdm_kline_1m_open.json")),
            _message(_load_fixture("usdm_kline_1m_closed.json")),
        ]
    )

    result = asyncio.run(
        run_local_btc_futures_binance_dry_run(
            RunLocalBtcFuturesBinanceDryRunRequest(
                config=LocalBtcFuturesDryRunConfig(
                    event_log_path=tmp_path / "events.jsonl",
                    strategy_config=BtcFuturesDemoStrategyConfig(ema_period=2),
                ),
                duration_seconds=10,
                max_messages=3,
            ),
            clock=FixedClock(NOW),
            clients=(client,),
            telemetry=telemetry,
        )
    )

    assert client.closed
    assert result.received_message_count == 3
    assert result.feed_state.closed_bar_count == 2
    assert result.feed_state.ignored_message_count == 1
    event_rows = read_jsonl_execution_events(tmp_path / "events.jsonl")
    assert [row["event_type"] for row in event_rows] == [
        "runtime_started",
        "heartbeat_recorded",
        "market_event_received",
        "market_event_received",
        "heartbeat_recorded",
        "runtime_stopped",
    ]
    status_view = result.runtime.state_repository.latest_status_view(
        ExecutionReadModelQuery(runtime_id=result.runtime.config.runtime_id)
    )
    assert status_view is not None
    assert status_view.status.value == "stopped"
    assert status_view.current_signal == "no_signal"
    assert status_view.paper_equity == Decimal("10000")
    assert [event.event_type.value for event in status_view.recent_events] == [
        "runtime_started",
        "heartbeat_recorded",
        "market_event_received",
        "market_event_received",
        "heartbeat_recorded",
        "runtime_stopped",
    ]
    assert len(telemetry.started) == 1
    assert len(telemetry.heartbeats) == 2
    assert telemetry.messages == [1, 2, 3]
    assert len(telemetry.stopped) == 1
