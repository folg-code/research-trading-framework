"""Tests for local BTC futures dry-run runtime assembly."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    create_local_btc_futures_dry_run_runtime,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import BestBidAskSnapshot, ExecutionEventType
from trading_framework.infrastructure.storage.execution_events import read_jsonl_execution_events
from trading_framework.strategy import BtcFuturesDemoStrategyConfig
from trading_framework.time.clocks.fixed import FixedClock

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def test_create_local_btc_futures_dry_run_runtime_assembles_components(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl"),
        clock=FixedClock(NOW),
    )

    assert runtime.config.symbol == "BTCUSDT"
    assert runtime.initial_state.account.equity == Decimal("10000")
    assert runtime.initial_state.position.quantity == Decimal("0")
    assert runtime.session.latest_status(runtime.config.runtime_id) is None


def test_local_btc_futures_runtime_decision_step_writes_jsonl_events(tmp_path: Path) -> None:
    event_log_path = tmp_path / "execution" / "events.jsonl"
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=event_log_path),
        clock=FixedClock(NOW),
    )
    quote = BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )

    result = runtime.decision_step.run(
        entry_signal_active=True,
        exit_signal_active=False,
        position=runtime.initial_state.position,
        quote=quote,
    )

    assert result.order_submitted
    rows = read_jsonl_execution_events(event_log_path)
    assert [row["event_type"] for row in rows] == [
        ExecutionEventType.MARKET_EVENT_RECEIVED.value,
        ExecutionEventType.ORDER_INTENT_CREATED.value,
        ExecutionEventType.SIMULATED_ORDER_FILLED.value,
        ExecutionEventType.POSITION_UPDATED.value,
    ]
    assert rows[-1]["payload"]["side"] == "long"


def test_local_btc_futures_runtime_accepts_strategy_config(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            strategy_config=BtcFuturesDemoStrategyConfig(quantity=Decimal("0.002")),
        ),
        clock=FixedClock(NOW),
    )
    quote = BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )

    result = runtime.decision_step.run(
        entry_signal_active=True,
        exit_signal_active=False,
        position=runtime.initial_state.position,
        quote=quote,
    )

    assert result.broker_result is not None
    assert result.broker_result.position.quantity == Decimal("0.002")


def test_local_btc_futures_config_rejects_invalid_values(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="runtime_id"):
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            runtime_id=" ",
        )

    with pytest.raises(ValidationError, match="starting_equity"):
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            starting_equity=Decimal("0"),
        )
