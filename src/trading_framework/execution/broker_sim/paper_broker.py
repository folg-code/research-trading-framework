"""Paper broker and position accounting for dry-run execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price
from trading_framework.execution.models import (
    BestBidAskSnapshot,
    OrderIntent,
    OrderSide,
    OrderStatus,
    PaperAccountSnapshot,
    PaperPosition,
    PositionSide,
    SimulatedFill,
    SimulatedOrder,
)
from trading_framework.time.models.utc_instant import require_utc_aware


@final
@dataclass(frozen=True, slots=True)
class PaperBrokerState:
    """Current paper broker accounting state for one symbol."""

    account: PaperAccountSnapshot
    position: PaperPosition


@final
@dataclass(frozen=True, slots=True)
class PaperBrokerResult:
    """Result of accepting one order intent into the paper broker."""

    order: SimulatedOrder
    fill: SimulatedFill
    account: PaperAccountSnapshot
    position: PaperPosition


@final
@dataclass(slots=True)
class PaperBroker:
    """Simple simulated broker for one-symbol dry-run execution."""

    account_id: str
    symbol: str
    currency: str
    starting_equity: Decimal

    _realized_pnl: Decimal = Decimal("0")
    _position_quantity: Decimal = Decimal("0")
    _average_entry_price: Price | None = None
    _last_mark_price: Price | None = None
    _order_sequence: int = 0
    _fill_sequence: int = 0

    def initial_state(self, recorded_at: datetime) -> PaperBrokerState:
        """Return the initial flat broker state."""
        timestamp = require_utc_aware(recorded_at)
        return PaperBrokerState(
            account=self._account_snapshot(timestamp),
            position=self._position_snapshot(timestamp),
        )

    def accept_market_order(
        self,
        intent: OrderIntent,
        quote: BestBidAskSnapshot,
    ) -> PaperBrokerResult:
        """Simulate a market order fill against the current best bid/ask snapshot."""
        self._validate_intent(intent, quote)
        fill_price = quote.ask_price if intent.side is OrderSide.BUY else quote.bid_price
        self._order_sequence += 1
        self._fill_sequence += 1
        order = SimulatedOrder(
            order_id=f"paper-order-{self._order_sequence}",
            intent_id=intent.intent_id,
            strategy_id=intent.strategy_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=intent.order_type,
            quantity=intent.quantity,
            status=OrderStatus.SIMULATED_FILLED,
            created_at=intent.requested_at,
        )
        fill = SimulatedFill(
            fill_id=f"paper-fill-{self._fill_sequence}",
            order_id=order.order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            price=fill_price,
            filled_at=quote.received_at or quote.event_at,
        )
        self._apply_fill(fill)
        account = self._account_snapshot(fill.filled_at)
        position = self._position_snapshot(fill.filled_at)
        return PaperBrokerResult(order=order, fill=fill, account=account, position=position)

    def mark_to_market(self, mark_price: Price, recorded_at: datetime) -> PaperBrokerState:
        """Update mark price and return current account and position snapshots."""
        timestamp = require_utc_aware(recorded_at)
        self._last_mark_price = mark_price
        return PaperBrokerState(
            account=self._account_snapshot(timestamp),
            position=self._position_snapshot(timestamp),
        )

    def _validate_intent(self, intent: OrderIntent, quote: BestBidAskSnapshot) -> None:
        if intent.symbol != self.symbol:
            msg = "order intent symbol must match broker symbol"
            raise ValidationError(msg)
        if quote.symbol != self.symbol:
            msg = "quote symbol must match broker symbol"
            raise ValidationError(msg)

    def _apply_fill(self, fill: SimulatedFill) -> None:
        self._last_mark_price = fill.price
        signed_quantity = fill.quantity if fill.side is OrderSide.BUY else -fill.quantity
        current_quantity = self._position_quantity
        new_quantity = current_quantity + signed_quantity
        if current_quantity == 0 or _same_direction(current_quantity, signed_quantity):
            self._increase_position(current_quantity, signed_quantity, fill.price)
        elif new_quantity == 0:
            self._realized_pnl += self._closing_pnl(abs(signed_quantity), fill.price)
            self._position_quantity = Decimal("0")
            self._average_entry_price = None
        elif _same_direction(current_quantity, new_quantity):
            closed_quantity = min(abs(signed_quantity), abs(current_quantity))
            self._realized_pnl += self._closing_pnl(closed_quantity, fill.price)
            self._position_quantity = new_quantity
        else:
            closed_quantity = abs(current_quantity)
            self._realized_pnl += self._closing_pnl(closed_quantity, fill.price)
            self._position_quantity = new_quantity
            self._average_entry_price = fill.price

    def _increase_position(
        self,
        current_quantity: Decimal,
        signed_quantity: Decimal,
        fill_price: Price,
    ) -> None:
        new_quantity = current_quantity + signed_quantity
        if current_quantity == 0 or self._average_entry_price is None:
            self._average_entry_price = fill_price
            self._position_quantity = new_quantity
            return
        weighted_notional = (
            abs(current_quantity) * self._average_entry_price.value
            + abs(signed_quantity) * fill_price.value
        )
        average_price = weighted_notional / abs(new_quantity)
        self._average_entry_price = Price(average_price)
        self._position_quantity = new_quantity

    def _closing_pnl(self, closed_quantity: Decimal, fill_price: Price) -> Decimal:
        if self._average_entry_price is None:
            return Decimal("0")
        if self._position_quantity > 0:
            return (fill_price.value - self._average_entry_price.value) * closed_quantity
        return (self._average_entry_price.value - fill_price.value) * closed_quantity

    def _position_snapshot(self, updated_at: datetime) -> PaperPosition:
        quantity = abs(self._position_quantity)
        side = _position_side(self._position_quantity)
        return PaperPosition(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            average_entry_price=self._average_entry_price,
            mark_price=self._last_mark_price,
            unrealized_pnl=self._unrealized_pnl(),
            updated_at=updated_at,
        )

    def _account_snapshot(self, updated_at: datetime) -> PaperAccountSnapshot:
        unrealized_pnl = self._unrealized_pnl()
        return PaperAccountSnapshot(
            account_id=self.account_id,
            currency=self.currency,
            starting_equity=self.starting_equity,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=unrealized_pnl,
            equity=self.starting_equity + self._realized_pnl + unrealized_pnl,
            updated_at=updated_at,
        )

    def _unrealized_pnl(self) -> Decimal:
        if (
            self._position_quantity == 0
            or self._average_entry_price is None
            or self._last_mark_price is None
        ):
            return Decimal("0")
        quantity = abs(self._position_quantity)
        if self._position_quantity > 0:
            return (self._last_mark_price.value - self._average_entry_price.value) * quantity
        return (self._average_entry_price.value - self._last_mark_price.value) * quantity


def _same_direction(left: Decimal, right: Decimal) -> bool:
    return (left > 0 and right > 0) or (left < 0 and right < 0)


def _position_side(quantity: Decimal) -> PositionSide:
    if quantity > 0:
        return PositionSide.LONG
    if quantity < 0:
        return PositionSide.SHORT
    return PositionSide.FLAT
