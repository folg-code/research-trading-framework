"""Tests for the read-only AWS execution status API handler."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from trading_framework.application.execution import handle_aws_execution_status_api_request
from trading_framework.core.types import Price
from trading_framework.execution import (
    ExecutionMode,
    ExecutionReadModelQuery,
    ExecutionStateRepository,
    PaperPosition,
    PositionSide,
    RuntimeHealth,
    RuntimeStatusView,
)

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class FakeExecutionStatusRepository:
    status: RuntimeStatusView | None
    query: ExecutionReadModelQuery | None = None

    def latest_status_view(self, query: ExecutionReadModelQuery) -> RuntimeStatusView | None:
        self.query = query
        return self.status

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[object, ...]:
        self.query = query
        return ()


def test_aws_status_api_returns_sanitized_runtime_status() -> None:
    repository = FakeExecutionStatusRepository(status=_status())

    response = handle_aws_execution_status_api_request(
        {"requestContext": {"http": {"method": "GET"}}},
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_RUNTIME_ID": "aws-runtime-1",
            "TRADING_FRAMEWORK_STATUS_API_CORS_ORIGIN": "https://portfolio.example.com",
            "TRADING_FRAMEWORK_STATUS_API_RECENT_EVENTS": "7",
            "TRADING_FRAMEWORK_STATUS_API_RECENT_ORDERS": "3",
            "TRADING_FRAMEWORK_STATUS_API_RECENT_FILLS": "2",
        },
        repository=cast(ExecutionStateRepository, repository),
    )

    payload = cast("dict[str, Any]", json.loads(str(response["body"])))
    assert response["statusCode"] == 200
    assert response["headers"]["Access-Control-Allow-Origin"] == "https://portfolio.example.com"
    assert response["headers"]["Cache-Control"] == "no-store"
    assert payload["runtime_id"] == "aws-runtime-1"
    assert payload["symbol"] == "BTCUSDT"
    assert payload["status"] == "running"
    assert payload["paper_equity"] == "10010"
    assert payload["current_position"]["side"] == "long"
    assert payload["simulated"] is True
    assert repository.query == ExecutionReadModelQuery(
        runtime_id="aws-runtime-1",
        recent_event_limit=7,
        recent_order_limit=3,
        recent_fill_limit=2,
    )
    assert "execution_state_table" not in payload


def test_aws_status_api_returns_404_when_status_is_missing() -> None:
    response = handle_aws_execution_status_api_request(
        {"httpMethod": "GET"},
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
        },
        repository=cast(ExecutionStateRepository, FakeExecutionStatusRepository(status=None)),
    )

    payload = cast("dict[str, Any]", json.loads(str(response["body"])))
    assert response["statusCode"] == 404
    assert payload["error"] == "runtime_status_not_found"
    assert payload["runtime_id"] == "btc-futures-dry-run-aws"
    assert payload["simulated"] is True


def test_aws_status_api_rejects_mutation_methods() -> None:
    response = handle_aws_execution_status_api_request(
        {"requestContext": {"http": {"method": "POST"}}},
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
        },
        repository=cast(ExecutionStateRepository, FakeExecutionStatusRepository(status=_status())),
    )

    payload = cast("dict[str, Any]", json.loads(str(response["body"])))
    assert response["statusCode"] == 405
    assert response["headers"]["Allow"] == "GET"
    assert payload["error"] == "method_not_allowed"


def test_aws_status_api_returns_error_for_invalid_configuration() -> None:
    response = handle_aws_execution_status_api_request(
        {"httpMethod": "GET"},
        {},
        repository=cast(ExecutionStateRepository, FakeExecutionStatusRepository(status=_status())),
    )

    payload = cast("dict[str, Any]", json.loads(str(response["body"])))
    assert response["statusCode"] == 500
    assert payload["error"] == "status_unavailable"
    assert "TRADING_FRAMEWORK_AWS_REGION" in payload["message"]
    assert payload["simulated"] is True


def _status() -> RuntimeStatusView:
    return RuntimeStatusView(
        runtime_id="aws-runtime-1",
        mode=ExecutionMode.DRY_RUN,
        provider="binance_usdm",
        symbol="BTCUSDT",
        status=RuntimeHealth.RUNNING,
        generated_at=NOW,
        last_heartbeat_at=NOW,
        last_market_event_at=NOW,
        last_price=Price(Decimal("65010")),
        current_signal="entry_signal_active",
        current_position=PaperPosition(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.001"),
            average_entry_price=Price(Decimal("65000")),
            mark_price=Price(Decimal("65010")),
            unrealized_pnl=Decimal("10"),
            updated_at=NOW,
        ),
        paper_equity=Decimal("10010"),
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("10"),
    )
