"""Tests for the local execution status CLI."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from pytest import CaptureFixture
from scripts.execution import show_execution_status

from trading_framework.core.types import Price
from trading_framework.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionMode,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperAccountSnapshot,
    PaperPosition,
    PositionSide,
    RuntimeHealth,
    RuntimeStatusSnapshot,
    SimulatedFill,
    SimulatedOrder,
)
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository

NOW = datetime(2026, 7, 16, 8, 0, tzinfo=UTC)


def test_show_execution_status_cli_prints_latest_read_model_json(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    repository = JsonExecutionStateRepository(tmp_path)
    repository.save_runtime_status(_status())
    repository.save_position("runtime-1", _position())
    repository.save_account("runtime-1", _account())
    repository.save_order("runtime-1", _order("order-1", NOW))
    repository.save_order("runtime-1", _order("order-2", NOW + timedelta(seconds=1)))
    repository.save_fill("runtime-1", _fill("fill-1", "order-1", NOW))
    repository.save_fill("runtime-1", _fill("fill-2", "order-2", NOW + timedelta(seconds=1)))
    repository.append_event("runtime-1", _event("event-1", NOW))
    repository.append_event("runtime-1", _event("event-2", NOW + timedelta(seconds=1)))

    exit_code = show_execution_status.main(
        [
            "--state-repository",
            str(tmp_path),
            "--runtime-id",
            "runtime-1",
            "--recent-events",
            "1",
            "--recent-orders",
            "1",
            "--recent-fills",
            "1",
        ]
    )

    captured = capsys.readouterr()
    payload = cast("dict[str, Any]", json.loads(captured.out))
    assert exit_code == 0
    assert captured.err == ""
    assert payload["runtime_id"] == "runtime-1"
    assert payload["mode"] == "dry_run"
    assert payload["provider"] == "binance_usdm"
    assert payload["symbol"] == "BTCUSDT"
    assert payload["status"] == "running"
    assert payload["paper_equity"] == "10010"
    assert payload["current_position"]["side"] == "long"
    assert payload["current_position"]["mark_price"] == "65010"
    assert [order["order_id"] for order in payload["recent_orders"]] == ["order-2"]
    assert [fill["fill_id"] for fill in payload["recent_fills"]] == ["fill-2"]
    assert [event["event_id"] for event in payload["recent_events"]] == ["event-2"]
    assert payload["simulated"] is True


def test_show_execution_status_cli_returns_error_for_missing_runtime(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    exit_code = show_execution_status.main(
        ["--state-repository", str(tmp_path), "--runtime-id", "missing-runtime"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "missing-runtime" in captured.err


def _status() -> RuntimeStatusSnapshot:
    return RuntimeStatusSnapshot(
        runtime_id="runtime-1",
        mode=ExecutionMode.DRY_RUN,
        status=RuntimeHealth.RUNNING,
        provider="binance_usdm",
        symbol="BTCUSDT",
        last_heartbeat_at=NOW,
        last_market_event_at=NOW - timedelta(seconds=5),
        current_signal="entry_signal_active",
    )


def _event(event_id: str, occurred_at: datetime) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=event_id,
        event_type=ExecutionEventType.HEARTBEAT_RECORDED,
        occurred_at=occurred_at,
        mode=ExecutionMode.DRY_RUN.value,
        symbol="BTCUSDT",
        payload={"runtime_id": "runtime-1", "simulated": "true"},
    )


def _order(order_id: str, created_at: datetime) -> SimulatedOrder:
    return SimulatedOrder(
        order_id=order_id,
        intent_id=f"intent-{order_id}",
        strategy_id="strategy-1",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
        status=OrderStatus.SIMULATED_FILLED,
        created_at=created_at,
    )


def _fill(fill_id: str, order_id: str, filled_at: datetime) -> SimulatedFill:
    return SimulatedFill(
        fill_id=fill_id,
        order_id=order_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.001"),
        price=Price(Decimal("65000")),
        filled_at=filled_at,
    )


def _position() -> PaperPosition:
    return PaperPosition(
        symbol="BTCUSDT",
        side=PositionSide.LONG,
        quantity=Decimal("0.001"),
        average_entry_price=Price(Decimal("65000")),
        mark_price=Price(Decimal("65010")),
        unrealized_pnl=Decimal("10"),
        updated_at=NOW,
    )


def _account() -> PaperAccountSnapshot:
    return PaperAccountSnapshot(
        account_id="paper-btc",
        currency="USDT",
        starting_equity=Decimal("10000"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("10"),
        equity=Decimal("10010"),
        updated_at=NOW,
    )
