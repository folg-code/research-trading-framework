"""Read-model contracts for dry-run execution state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution.models import (
    ExecutionEvent,
    ExecutionEventType,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperPosition,
    RuntimeHealth,
)
from trading_framework.execution.models._validation import (
    normalize_decimal,
    normalize_non_empty,
    normalize_positive_decimal,
)
from trading_framework.execution.modes import ExecutionMode
from trading_framework.time.models.utc_instant import require_utc_aware

DEFAULT_RECENT_EVENT_LIMIT = 50
DEFAULT_RECENT_ORDER_LIMIT = 20
DEFAULT_RECENT_FILL_LIMIT = 20


@final
@dataclass(frozen=True, slots=True)
class ExecutionReadModelQuery:
    """Read-only query bounds for one runtime read model."""

    runtime_id: str
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT
    recent_fill_limit: int = DEFAULT_RECENT_FILL_LIMIT

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_id", normalize_non_empty(self.runtime_id, "runtime_id"))
        _require_positive_limit(self.recent_event_limit, "recent_event_limit")
        _require_positive_limit(self.recent_order_limit, "recent_order_limit")
        _require_positive_limit(self.recent_fill_limit, "recent_fill_limit")


@final
@dataclass(frozen=True, slots=True)
class RecentExecutionEventView:
    """Recent execution event item for dashboards and APIs."""

    event_id: str
    event_type: ExecutionEventType
    occurred_at: datetime
    symbol: str
    payload: Mapping[str, str] | None = None
    correlation_id: str | None = None
    simulated: bool = True

    def __post_init__(self) -> None:
        occurred_at = require_utc_aware(self.occurred_at)
        if occurred_at != self.occurred_at:
            object.__setattr__(self, "occurred_at", occurred_at)
        object.__setattr__(self, "event_id", normalize_non_empty(self.event_id, "event_id"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.correlation_id is not None:
            object.__setattr__(
                self,
                "correlation_id",
                normalize_non_empty(self.correlation_id, "correlation_id"),
            )
        if self.payload is not None:
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if not self.simulated:
            msg = "RecentExecutionEventView must be marked simulated"
            raise ValidationError(msg)

    @classmethod
    def from_event(cls, event: ExecutionEvent) -> RecentExecutionEventView:
        """Create a read-model event item from an execution event fact."""
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            symbol=event.symbol,
            payload=event.payload,
            correlation_id=event.correlation_id,
        )


@final
@dataclass(frozen=True, slots=True)
class RecentOrderView:
    """Recent simulated order item for execution dashboards."""

    order_id: str
    intent_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    status: OrderStatus
    created_at: datetime
    simulated: bool = True

    def __post_init__(self) -> None:
        created_at = require_utc_aware(self.created_at)
        if created_at != self.created_at:
            object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "order_id", normalize_non_empty(self.order_id, "order_id"))
        object.__setattr__(self, "intent_id", normalize_non_empty(self.intent_id, "intent_id"))
        object.__setattr__(
            self,
            "strategy_id",
            normalize_non_empty(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        object.__setattr__(self, "quantity", normalize_positive_decimal(self.quantity, "quantity"))
        if not self.simulated:
            msg = "RecentOrderView must be marked simulated"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class RecentFillView:
    """Recent simulated fill item for execution dashboards."""

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Price
    filled_at: datetime
    liquidity: str = "simulated"
    simulated: bool = True

    def __post_init__(self) -> None:
        filled_at = require_utc_aware(self.filled_at)
        if filled_at != self.filled_at:
            object.__setattr__(self, "filled_at", filled_at)
        object.__setattr__(self, "fill_id", normalize_non_empty(self.fill_id, "fill_id"))
        object.__setattr__(self, "order_id", normalize_non_empty(self.order_id, "order_id"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        object.__setattr__(self, "quantity", normalize_positive_decimal(self.quantity, "quantity"))
        object.__setattr__(self, "liquidity", normalize_non_empty(self.liquidity, "liquidity"))
        if not self.simulated:
            msg = "RecentFillView must be marked simulated"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class RuntimeStatusView:
    """Dashboard-ready read model for one dry-run runtime."""

    runtime_id: str
    mode: ExecutionMode
    provider: str
    symbol: str
    status: RuntimeHealth
    generated_at: datetime
    last_heartbeat_at: datetime
    last_market_event_at: datetime | None = None
    last_price: Price | None = None
    current_signal: str | None = None
    current_position: PaperPosition | None = None
    paper_equity: Decimal | None = None
    realized_pnl: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    recent_orders: tuple[RecentOrderView, ...] = ()
    recent_fills: tuple[RecentFillView, ...] = ()
    recent_events: tuple[RecentExecutionEventView, ...] = ()
    simulated: bool = True

    def __post_init__(self) -> None:
        generated_at = require_utc_aware(self.generated_at)
        heartbeat_at = require_utc_aware(self.last_heartbeat_at)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "last_heartbeat_at", heartbeat_at)
        if self.last_market_event_at is not None:
            object.__setattr__(
                self,
                "last_market_event_at",
                require_utc_aware(self.last_market_event_at),
            )
        object.__setattr__(self, "runtime_id", normalize_non_empty(self.runtime_id, "runtime_id"))
        object.__setattr__(self, "provider", normalize_non_empty(self.provider, "provider"))
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        if self.current_signal is not None:
            object.__setattr__(
                self,
                "current_signal",
                normalize_non_empty(self.current_signal, "current_signal"),
            )
        if self.paper_equity is not None:
            object.__setattr__(
                self,
                "paper_equity",
                normalize_decimal(self.paper_equity, "paper_equity"),
            )
        if self.realized_pnl is not None:
            object.__setattr__(
                self,
                "realized_pnl",
                normalize_decimal(self.realized_pnl, "realized_pnl"),
            )
        if self.unrealized_pnl is not None:
            object.__setattr__(
                self,
                "unrealized_pnl",
                normalize_decimal(self.unrealized_pnl, "unrealized_pnl"),
            )
        if not self.simulated:
            msg = "RuntimeStatusView must be marked simulated"
            raise ValidationError(msg)

    def is_stale(self, *, reference_time: datetime, stale_after: timedelta) -> bool:
        """Return whether the last heartbeat is older than the accepted freshness window."""
        if stale_after <= timedelta(0):
            msg = "stale_after must be positive"
            raise ValidationError(msg)
        reference = require_utc_aware(reference_time)
        return reference - self.last_heartbeat_at > stale_after


def _require_positive_limit(value: int, field_name: str) -> None:
    if value < 1:
        msg = f"{field_name} must be positive"
        raise ValidationError(msg)
