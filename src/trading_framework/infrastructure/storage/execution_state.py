"""Local JSON adapter for execution state read models."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, final
from urllib.parse import quote

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.execution.models import (
    ExecutionEvent,
    ExecutionEventType,
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
from trading_framework.execution.models._validation import normalize_non_empty
from trading_framework.execution.modes import ExecutionMode
from trading_framework.execution.repositories.read_models import (
    DEFAULT_RECENT_BAR_LIMIT,
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
    RecentBarView,
    RecentExecutionEventView,
    RecentFillView,
    RecentOrderView,
    RuntimeStatusView,
)
from trading_framework.market.models import MarketBar
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

_STATE_FILE_NAME = "state.json"
_STATE_VERSION = 1


@final
@dataclass(frozen=True, slots=True)
class JsonExecutionStateRepository:
    """Persist one local read model per runtime as explicit JSON documents."""

    base_path: Path
    clock: Clock = field(default_factory=SystemClock)
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT
    recent_fill_limit: int = DEFAULT_RECENT_FILL_LIMIT
    recent_bar_limit: int = DEFAULT_RECENT_BAR_LIMIT

    def __post_init__(self) -> None:
        _require_positive_limit(self.recent_event_limit, "recent_event_limit")
        _require_positive_limit(self.recent_order_limit, "recent_order_limit")
        _require_positive_limit(self.recent_fill_limit, "recent_fill_limit")
        _require_positive_limit(self.recent_bar_limit, "recent_bar_limit")

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

    def save_bar(self, runtime_id: str, bar: MarketBar) -> None:
        """Persist or update one recent closed OHLCV bar."""
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        state = self._load_state(runtime_id)
        view = _bar_to_view(bar)
        bars = [
            item
            for item in state["bars"]
            if item.get("observed_at") != _datetime_to_json(view.observed_at)
        ]
        bars.append(_bar_view_to_json(view))
        state["bars"] = _tail(bars, self.recent_bar_limit)
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
            recent_bars=self.recent_bars(query),
        )

    def recent_events(self, query: ExecutionReadModelQuery) -> tuple[RecentExecutionEventView, ...]:
        """Return bounded recent execution events for one runtime."""
        state = self._load_state(query.runtime_id)
        return tuple(
            _event_view_from_json(item)
            for item in _tail(list(state["events"]), query.recent_event_limit)
        )

    def recent_bars(self, query: ExecutionReadModelQuery) -> tuple[RecentBarView, ...]:
        """Return bounded recent closed market bars for one runtime."""
        state = self._load_state(query.runtime_id)
        return tuple(
            _bar_view_from_json(item) for item in _tail(list(state["bars"]), query.recent_bar_limit)
        )

    def _load_state(self, runtime_id: str) -> dict[str, Any]:
        path = self._state_path(runtime_id)
        if not path.exists():
            return _empty_state()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != _STATE_VERSION:
            msg = "unsupported execution state version"
            raise ValidationError(msg)
        return {
            "version": payload["version"],
            "status": payload.get("status"),
            "events": list(payload.get("events", ())),
            "orders": list(payload.get("orders", ())),
            "fills": list(payload.get("fills", ())),
            "bars": list(payload.get("bars", ())),
            "position": payload.get("position"),
            "account": payload.get("account"),
        }

    def _write_state(self, runtime_id: str, state: Mapping[str, Any]) -> None:
        path = self._state_path(runtime_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        text = json.dumps(state, indent=2, sort_keys=True)
        temporary_path.write_text(f"{text}\n", encoding="utf-8")
        temporary_path.replace(path)

    def _state_path(self, runtime_id: str) -> Path:
        runtime_id = normalize_non_empty(runtime_id, "runtime_id")
        return self.base_path / quote(runtime_id, safe="") / _STATE_FILE_NAME


def _empty_state() -> dict[str, Any]:
    return {
        "version": _STATE_VERSION,
        "status": None,
        "events": [],
        "orders": [],
        "fills": [],
        "bars": [],
        "position": None,
        "account": None,
    }


def _bar_to_view(bar: MarketBar) -> RecentBarView:
    return RecentBarView(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        observed_at=bar.observed_at,
        available_at=bar.available_at,
    )


def _bar_view_to_json(view: RecentBarView) -> dict[str, Any]:
    return {
        "open": view.open.to_json(),
        "high": view.high.to_json(),
        "low": view.low.to_json(),
        "close": view.close.to_json(),
        "volume": view.volume.to_json(),
        "observed_at": _datetime_to_json(view.observed_at),
        "available_at": _datetime_to_json(view.available_at),
        "simulated": view.simulated,
    }


def _bar_view_from_json(payload: Mapping[str, Any]) -> RecentBarView:
    return RecentBarView(
        open=Price.from_json(str(payload["open"])),
        high=Price.from_json(str(payload["high"])),
        low=Price.from_json(str(payload["low"])),
        close=Price.from_json(str(payload["close"])),
        volume=Volume.from_json(int(payload["volume"])),
        observed_at=_datetime_from_json(str(payload["observed_at"])),
        available_at=_datetime_from_json(str(payload["available_at"])),
        simulated=bool(payload.get("simulated", True)),
    )


def _order_to_view(order: SimulatedOrder) -> RecentOrderView:
    return RecentOrderView(
        order_id=order.order_id,
        intent_id=order.intent_id,
        strategy_id=order.strategy_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.quantity,
        status=order.status,
        created_at=order.created_at,
    )


def _fill_to_view(fill: SimulatedFill) -> RecentFillView:
    return RecentFillView(
        fill_id=fill.fill_id,
        order_id=fill.order_id,
        symbol=fill.symbol,
        side=fill.side,
        quantity=fill.quantity,
        price=fill.price,
        filled_at=fill.filled_at,
        liquidity=fill.liquidity,
    )


def _status_to_json(status: RuntimeStatusSnapshot) -> dict[str, Any]:
    return {
        "runtime_id": status.runtime_id,
        "mode": status.mode.value,
        "status": status.status.value,
        "provider": status.provider,
        "symbol": status.symbol,
        "last_heartbeat_at": _datetime_to_json(status.last_heartbeat_at),
        "last_market_event_at": _optional_datetime_to_json(status.last_market_event_at),
        "current_signal": status.current_signal,
        "simulated": status.simulated,
    }


def _status_from_json(payload: Mapping[str, Any]) -> RuntimeStatusSnapshot:
    return RuntimeStatusSnapshot(
        runtime_id=str(payload["runtime_id"]),
        mode=ExecutionMode(str(payload["mode"])),
        status=RuntimeHealth(str(payload["status"])),
        provider=str(payload["provider"]),
        symbol=str(payload["symbol"]),
        last_heartbeat_at=_datetime_from_json(str(payload["last_heartbeat_at"])),
        last_market_event_at=_optional_datetime_from_json(payload.get("last_market_event_at")),
        current_signal=_optional_str(payload.get("current_signal")),
        simulated=bool(payload.get("simulated", True)),
    )


def _event_view_to_json(view: RecentExecutionEventView) -> dict[str, Any]:
    payload = view.payload
    return {
        "event_id": view.event_id,
        "event_type": view.event_type.value,
        "occurred_at": _datetime_to_json(view.occurred_at),
        "symbol": view.symbol,
        "payload": dict(payload) if payload is not None else None,
        "correlation_id": view.correlation_id,
        "simulated": view.simulated,
    }


def _event_view_from_json(payload: Mapping[str, Any]) -> RecentExecutionEventView:
    raw_payload = payload.get("payload")
    event_payload = _string_mapping(raw_payload) if raw_payload is not None else None
    return RecentExecutionEventView(
        event_id=str(payload["event_id"]),
        event_type=ExecutionEventType(str(payload["event_type"])),
        occurred_at=_datetime_from_json(str(payload["occurred_at"])),
        symbol=str(payload["symbol"]),
        payload=event_payload,
        correlation_id=_optional_str(payload.get("correlation_id")),
        simulated=bool(payload.get("simulated", True)),
    )


def _order_view_to_json(view: RecentOrderView) -> dict[str, Any]:
    return {
        "order_id": view.order_id,
        "intent_id": view.intent_id,
        "strategy_id": view.strategy_id,
        "symbol": view.symbol,
        "side": view.side.value,
        "order_type": view.order_type.value,
        "quantity": _decimal_to_json(view.quantity),
        "status": view.status.value,
        "created_at": _datetime_to_json(view.created_at),
        "simulated": view.simulated,
    }


def _order_view_from_json(payload: Mapping[str, Any]) -> RecentOrderView:
    return RecentOrderView(
        order_id=str(payload["order_id"]),
        intent_id=str(payload["intent_id"]),
        strategy_id=str(payload["strategy_id"]),
        symbol=str(payload["symbol"]),
        side=OrderSide(str(payload["side"])),
        order_type=OrderType(str(payload["order_type"])),
        quantity=_decimal_from_json(payload["quantity"]),
        status=OrderStatus(str(payload["status"])),
        created_at=_datetime_from_json(str(payload["created_at"])),
        simulated=bool(payload.get("simulated", True)),
    )


def _fill_view_to_json(view: RecentFillView) -> dict[str, Any]:
    return {
        "fill_id": view.fill_id,
        "order_id": view.order_id,
        "symbol": view.symbol,
        "side": view.side.value,
        "quantity": _decimal_to_json(view.quantity),
        "price": view.price.to_json(),
        "filled_at": _datetime_to_json(view.filled_at),
        "liquidity": view.liquidity,
        "simulated": view.simulated,
    }


def _fill_view_from_json(payload: Mapping[str, Any]) -> RecentFillView:
    return RecentFillView(
        fill_id=str(payload["fill_id"]),
        order_id=str(payload["order_id"]),
        symbol=str(payload["symbol"]),
        side=OrderSide(str(payload["side"])),
        quantity=_decimal_from_json(payload["quantity"]),
        price=Price.from_json(str(payload["price"])),
        filled_at=_datetime_from_json(str(payload["filled_at"])),
        liquidity=str(payload["liquidity"]),
        simulated=bool(payload.get("simulated", True)),
    )


def _position_to_json(position: PaperPosition) -> dict[str, Any]:
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


def _position_from_json(payload: Mapping[str, Any]) -> PaperPosition:
    return PaperPosition(
        symbol=str(payload["symbol"]),
        side=PositionSide(str(payload["side"])),
        quantity=_decimal_from_json(payload["quantity"]),
        average_entry_price=_optional_price_from_json(payload.get("average_entry_price")),
        mark_price=_optional_price_from_json(payload.get("mark_price")),
        unrealized_pnl=_decimal_from_json(payload["unrealized_pnl"]),
        updated_at=_datetime_from_json(str(payload["updated_at"])),
        simulated=bool(payload.get("simulated", True)),
    )


def _account_to_json(account: PaperAccountSnapshot) -> dict[str, Any]:
    return {
        "account_id": account.account_id,
        "currency": account.currency,
        "starting_equity": _decimal_to_json(account.starting_equity),
        "realized_pnl": _decimal_to_json(account.realized_pnl),
        "unrealized_pnl": _decimal_to_json(account.unrealized_pnl),
        "equity": _decimal_to_json(account.equity),
        "updated_at": _datetime_to_json(account.updated_at),
        "simulated": account.simulated,
    }


def _account_from_json(payload: Mapping[str, Any]) -> PaperAccountSnapshot:
    return PaperAccountSnapshot(
        account_id=str(payload["account_id"]),
        currency=str(payload["currency"]),
        starting_equity=_decimal_from_json(payload["starting_equity"]),
        realized_pnl=_decimal_from_json(payload["realized_pnl"]),
        unrealized_pnl=_decimal_from_json(payload["unrealized_pnl"]),
        equity=_decimal_from_json(payload["equity"]),
        updated_at=_datetime_from_json(str(payload["updated_at"])),
        simulated=bool(payload.get("simulated", True)),
    )


def _tail(items: list[Any], limit: int) -> list[Any]:
    return items[-limit:]


def _require_positive_limit(value: int, field_name: str) -> None:
    if value < 1:
        msg = f"{field_name} must be positive"
        raise ValidationError(msg)


def _datetime_to_json(value: datetime) -> str:
    return value.isoformat()


def _datetime_from_json(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime_to_json(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _optional_datetime_from_json(value: object) -> datetime | None:
    return _datetime_from_json(str(value)) if value is not None else None


def _decimal_to_json(value: Decimal) -> str:
    return format(value, "f")


def _decimal_from_json(value: object) -> Decimal:
    return Decimal(str(value))


def _optional_price_to_json(value: Price | None) -> str | None:
    return value.to_json() if value is not None else None


def _optional_price_from_json(value: object) -> Price | None:
    return Price.from_json(str(value)) if value is not None else None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        msg = "event payload must be a JSON object"
        raise ValidationError(msg)
    return {str(key): str(item) for key, item in value.items()}
