"""DynamoDB adapter for execution state read models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, final

from trading_framework.core.exceptions import ValidationError
from trading_framework.execution.models import (
    ExecutionEvent,
    PaperAccountSnapshot,
    PaperPosition,
    RuntimeStatusSnapshot,
    SimulatedFill,
    SimulatedOrder,
)
from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.execution.repositories.read_models import (
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
    RecentExecutionEventView,
    RuntimeStatusView,
)
from trading_framework.infrastructure.storage.execution_state import (
    _account_from_json,
    _account_to_json,
    _empty_state,
    _event_view_from_json,
    _event_view_to_json,
    _fill_to_view,
    _fill_view_from_json,
    _fill_view_to_json,
    _order_to_view,
    _order_view_from_json,
    _order_view_to_json,
    _position_from_json,
    _position_to_json,
    _status_from_json,
    _status_to_json,
    _tail,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

_STATE_VERSION = 1
_STATE_SORT_KEY = "STATE"


class DynamoDbExecutionStateClient(Protocol):
    """Small subset of the low-level DynamoDB client used by the adapter."""

    def get_item(
        self,
        *,
        TableName: str,
        Key: Mapping[str, Mapping[str, str]],
        ConsistentRead: bool = False,
    ) -> Mapping[str, Any]:
        """Return one DynamoDB item."""
        ...

    def put_item(
        self,
        *,
        TableName: str,
        Item: Mapping[str, Mapping[str, str]],
    ) -> Mapping[str, Any]:
        """Persist one DynamoDB item."""
        ...


@final
@dataclass(frozen=True, slots=True)
class DynamoDbExecutionStateRepository:
    """Persist execution read model state in one DynamoDB document item per runtime."""

    client: DynamoDbExecutionStateClient
    table_name: str
    clock: Clock = field(default_factory=SystemClock)
    partition_key_name: str = "pk"
    sort_key_name: str = "sk"
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT
    recent_fill_limit: int = DEFAULT_RECENT_FILL_LIMIT

    def __post_init__(self) -> None:
        object.__setattr__(self, "table_name", normalize_non_empty(self.table_name, "table_name"))
        object.__setattr__(
            self,
            "partition_key_name",
            normalize_non_empty(self.partition_key_name, "partition_key_name"),
        )
        object.__setattr__(
            self,
            "sort_key_name",
            normalize_non_empty(self.sort_key_name, "sort_key_name"),
        )
        _require_positive_limit(self.recent_event_limit, "recent_event_limit")
        _require_positive_limit(self.recent_order_limit, "recent_order_limit")
        _require_positive_limit(self.recent_fill_limit, "recent_fill_limit")

    def append_event(self, runtime_id: str, event: ExecutionEvent) -> None:
        """Persist one immutable execution event in the bounded recent-events list."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        events = list(state["events"])
        events.append(_event_view_to_json(RecentExecutionEventView.from_event(event)))
        state["events"] = _tail(events, self.recent_event_limit)
        self._write_state(runtime_id, state)

    def save_runtime_status(self, status: RuntimeStatusSnapshot) -> None:
        """Persist the latest runtime status snapshot."""
        state = self._load_state(status.runtime_id)
        state["status"] = _status_to_json(status)
        self._write_state(status.runtime_id, state)

    def save_order(self, runtime_id: str, order: SimulatedOrder) -> None:
        """Persist or update one simulated order read-model item."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        orders = [item for item in state["orders"] if item.get("order_id") != order.order_id]
        orders.append(_order_view_to_json(_order_to_view(order)))
        state["orders"] = _tail(orders, self.recent_order_limit)
        self._write_state(runtime_id, state)

    def save_fill(self, runtime_id: str, fill: SimulatedFill) -> None:
        """Persist or update one simulated fill read-model item."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        fills = [item for item in state["fills"] if item.get("fill_id") != fill.fill_id]
        fills.append(_fill_view_to_json(_fill_to_view(fill)))
        state["fills"] = _tail(fills, self.recent_fill_limit)
        self._write_state(runtime_id, state)

    def save_position(self, runtime_id: str, position: PaperPosition) -> None:
        """Persist the latest paper position snapshot."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        state["position"] = _position_to_json(position)
        self._write_state(runtime_id, state)

    def save_account(self, runtime_id: str, account: PaperAccountSnapshot) -> None:
        """Persist the latest paper account snapshot."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        state["account"] = _account_to_json(account)
        self._write_state(runtime_id, state)

    def latest_status_view(self, query: ExecutionReadModelQuery) -> RuntimeStatusView | None:
        """Return the latest dashboard-ready status view for one runtime."""
        state = self._load_state(query.runtime_id)
        status_payload = state["status"]
        if status_payload is None:
            return None
        status = _status_from_json(status_payload)
        position_payload = state["position"]
        account_payload = state["account"]
        position = _position_from_json(position_payload) if position_payload is not None else None
        account = _account_from_json(account_payload) if account_payload is not None else None
        return RuntimeStatusView(
            runtime_id=status.runtime_id,
            mode=status.mode,
            provider=status.provider,
            symbol=status.symbol,
            status=status.status,
            generated_at=self.clock.now(),
            last_heartbeat_at=status.last_heartbeat_at,
            last_market_event_at=status.last_market_event_at,
            last_price=position.mark_price if position is not None else None,
            current_signal=status.current_signal,
            current_position=position,
            paper_equity=account.equity if account is not None else None,
            realized_pnl=account.realized_pnl if account is not None else None,
            unrealized_pnl=account.unrealized_pnl if account is not None else None,
            recent_orders=tuple(
                _order_view_from_json(item)
                for item in _tail(list(state["orders"]), query.recent_order_limit)
            ),
            recent_fills=tuple(
                _fill_view_from_json(item)
                for item in _tail(list(state["fills"]), query.recent_fill_limit)
            ),
            recent_events=self.recent_events(query),
        )

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[RecentExecutionEventView, ...]:
        """Return bounded recent execution events for one runtime."""
        state = self._load_state(query.runtime_id)
        return tuple(
            _event_view_from_json(item)
            for item in _tail(list(state["events"]), query.recent_event_limit)
        )

    def _load_state(self, runtime_id: str) -> dict[str, Any]:
        response = self.client.get_item(
            TableName=self.table_name,
            Key=self._key(runtime_id),
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            return _empty_state()
        if not isinstance(item, Mapping):
            msg = "DynamoDB execution state item must be a mapping"
            raise ValidationError(msg)
        version = _number_attribute(item, "version")
        if version != _STATE_VERSION:
            msg = "unsupported DynamoDB execution state version"
            raise ValidationError(msg)
        state_text = _string_attribute(item, "state_json")
        payload = json.loads(state_text)
        return {
            "version": version,
            "status": payload.get("status"),
            "events": list(payload.get("events", ())),
            "orders": list(payload.get("orders", ())),
            "fills": list(payload.get("fills", ())),
            "position": payload.get("position"),
            "account": payload.get("account"),
        }

    def _write_state(self, runtime_id: str, state: Mapping[str, Any]) -> None:
        state_payload = dict(state)
        self.client.put_item(
            TableName=self.table_name,
            Item={
                **self._key(runtime_id),
                "runtime_id": {"S": runtime_id},
                "version": {"N": str(_STATE_VERSION)},
                "updated_at": {"S": self.clock.now().isoformat()},
                "state_json": {"S": json.dumps(state_payload, sort_keys=True)},
            },
        )

    def _key(self, runtime_id: str) -> dict[str, dict[str, str]]:
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        return {
            self.partition_key_name: {"S": f"RUNTIME#{runtime_id}"},
            self.sort_key_name: {"S": _STATE_SORT_KEY},
        }


def _string_attribute(item: Mapping[str, Any], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, Mapping):
        msg = f"DynamoDB attribute {name} must be present"
        raise ValidationError(msg)
    raw = value.get("S")
    if not isinstance(raw, str):
        msg = f"DynamoDB attribute {name} must be a string"
        raise ValidationError(msg)
    return raw


def _number_attribute(item: Mapping[str, Any], name: str) -> int:
    value = item.get(name)
    if not isinstance(value, Mapping):
        msg = f"DynamoDB attribute {name} must be present"
        raise ValidationError(msg)
    raw = value.get("N")
    if not isinstance(raw, str):
        msg = f"DynamoDB attribute {name} must be a number"
        raise ValidationError(msg)
    return int(raw)


def _require_positive_limit(value: int, field_name: str) -> None:
    if value < 1:
        msg = f"{field_name} must be positive"
        raise ValidationError(msg)
