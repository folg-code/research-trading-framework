"""Dry-run order and fill contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution.models._validation import (
    normalize_non_empty,
    normalize_positive_decimal,
)
from trading_framework.time.models.utc_instant import require_utc_aware


class OrderSide(StrEnum):
    """Order direction."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Supported dry-run order types."""

    MARKET = "market"


class OrderStatus(StrEnum):
    """Dry-run order lifecycle state."""

    CREATED = "created"
    SIMULATED_FILLED = "simulated_filled"
    SIMULATED_REJECTED = "simulated_rejected"


@final
@dataclass(frozen=True, slots=True)
class OrderIntent:
    """A strategy request to create a simulated order."""

    intent_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    requested_at: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        requested_at = require_utc_aware(self.requested_at)
        if requested_at != self.requested_at:
            object.__setattr__(self, "requested_at", requested_at)
        object.__setattr__(self, "intent_id", normalize_non_empty(self.intent_id, "intent_id"))
        object.__setattr__(
            self,
            "strategy_id",
            normalize_non_empty(self.strategy_id, "strategy_id"),
        )
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        object.__setattr__(self, "quantity", normalize_positive_decimal(self.quantity, "quantity"))
        if self.reason is not None:
            object.__setattr__(self, "reason", normalize_non_empty(self.reason, "reason"))


@final
@dataclass(frozen=True, slots=True)
class SimulatedOrder:
    """An order tracked by the simulated broker."""

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
            msg = "SimulatedOrder must be marked simulated"
            raise ValidationError(msg)


@final
@dataclass(frozen=True, slots=True)
class SimulatedFill:
    """A simulated fill produced by the dry-run broker."""

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
            msg = "SimulatedFill must be marked simulated"
            raise ValidationError(msg)
