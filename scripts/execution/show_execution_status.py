"""Print the latest local execution read model as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import TradingFrameworkError, ValidationError
from trading_framework.core.types import Price
from trading_framework.execution import (
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
    RecentExecutionEventView,
    RecentFillView,
    RecentOrderView,
    RuntimeStatusView,
)
from trading_framework.execution.models import PaperPosition
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository

DEFAULT_STATE_REPOSITORY_PATH = Path("user_data/runtime/btc_futures_dry_run/state")
DEFAULT_RUNTIME_ID = "btc-futures-dry-run-local"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print the latest local execution read model as JSON.",
    )
    parser.add_argument(
        "--state-repository",
        type=Path,
        default=DEFAULT_STATE_REPOSITORY_PATH,
        help="Local JSON execution state repository path",
    )
    parser.add_argument("--runtime-id", default=DEFAULT_RUNTIME_ID)
    parser.add_argument(
        "--recent-events",
        type=int,
        default=DEFAULT_RECENT_EVENT_LIMIT,
        help="Maximum recent execution events to include",
    )
    parser.add_argument(
        "--recent-orders",
        type=int,
        default=DEFAULT_RECENT_ORDER_LIMIT,
        help="Maximum recent simulated orders to include",
    )
    parser.add_argument(
        "--recent-fills",
        type=int,
        default=DEFAULT_RECENT_FILL_LIMIT,
        help="Maximum recent simulated fills to include",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the read-only local execution status CLI."""
    args = _build_parser().parse_args(argv)
    try:
        query = ExecutionReadModelQuery(
            runtime_id=args.runtime_id,
            recent_event_limit=args.recent_events,
            recent_order_limit=args.recent_orders,
            recent_fill_limit=args.recent_fills,
        )
        repository = JsonExecutionStateRepository(args.state_repository)
        status = repository.latest_status_view(query)
    except (TradingFrameworkError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if status is None:
        print(f"no execution status found for runtime_id={query.runtime_id}", file=sys.stderr)
        return 1

    print(json.dumps(_runtime_status_view_to_json(status), sort_keys=True))
    return 0


def _runtime_status_view_to_json(view: RuntimeStatusView) -> dict[str, Any]:
    return {
        "runtime_id": view.runtime_id,
        "mode": view.mode.value,
        "provider": view.provider,
        "symbol": view.symbol,
        "status": view.status.value,
        "generated_at": _datetime_to_json(view.generated_at),
        "last_heartbeat_at": _datetime_to_json(view.last_heartbeat_at),
        "last_market_event_at": _optional_datetime_to_json(view.last_market_event_at),
        "last_price": _optional_price_to_json(view.last_price),
        "current_signal": view.current_signal,
        "current_position": _position_to_json(view.current_position),
        "paper_equity": _optional_decimal_to_json(view.paper_equity),
        "realized_pnl": _optional_decimal_to_json(view.realized_pnl),
        "unrealized_pnl": _optional_decimal_to_json(view.unrealized_pnl),
        "recent_orders": [_order_to_json(order) for order in view.recent_orders],
        "recent_fills": [_fill_to_json(fill) for fill in view.recent_fills],
        "recent_events": [_event_to_json(event) for event in view.recent_events],
        "simulated": view.simulated,
    }


def _order_to_json(order: RecentOrderView) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "intent_id": order.intent_id,
        "strategy_id": order.strategy_id,
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "quantity": _decimal_to_json(order.quantity),
        "status": order.status.value,
        "created_at": _datetime_to_json(order.created_at),
        "simulated": order.simulated,
    }


def _fill_to_json(fill: RecentFillView) -> dict[str, Any]:
    return {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "symbol": fill.symbol,
        "side": fill.side.value,
        "quantity": _decimal_to_json(fill.quantity),
        "price": fill.price.to_json(),
        "filled_at": _datetime_to_json(fill.filled_at),
        "liquidity": fill.liquidity,
        "simulated": fill.simulated,
    }


def _event_to_json(event: RecentExecutionEventView) -> dict[str, Any]:
    payload = event.payload
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "occurred_at": _datetime_to_json(event.occurred_at),
        "symbol": event.symbol,
        "payload": dict(payload) if payload is not None else None,
        "correlation_id": event.correlation_id,
        "simulated": event.simulated,
    }


def _position_to_json(position: PaperPosition | None) -> dict[str, Any] | None:
    if position is None:
        return None
    return {
        "symbol": position.symbol,
        "side": position.side.value,
        "quantity": _decimal_to_json(position.quantity),
        "average_entry_price": _optional_price_to_json(position.average_entry_price),
        "mark_price": _optional_price_to_json(position.mark_price),
        "unrealized_pnl": _decimal_to_json(position.unrealized_pnl),
        "updated_at": _datetime_to_json(position.updated_at),
        "simulated": position.simulated,
    }


def _datetime_to_json(value: datetime) -> str:
    return value.isoformat()


def _optional_datetime_to_json(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal_to_json(value: Decimal | None) -> str | None:
    return _decimal_to_json(value) if value is not None else None


def _optional_price_to_json(value: Price | None) -> str | None:
    return value.to_json() if value is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
