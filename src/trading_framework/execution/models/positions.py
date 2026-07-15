"""Paper position contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import final

from trading_framework.core.types import Price
from trading_framework.execution.models._validation import (
    normalize_decimal,
    normalize_non_empty,
    normalize_non_negative_decimal,
)
from trading_framework.time.models.utc_instant import require_utc_aware


class PositionSide(StrEnum):
    """Paper position side."""

    FLAT = "flat"
    LONG = "long"
    SHORT = "short"


@final
@dataclass(frozen=True, slots=True)
class PaperPosition:
    """Current simulated position for one symbol."""

    symbol: str
    side: PositionSide
    quantity: Decimal
    average_entry_price: Price | None
    mark_price: Price | None
    unrealized_pnl: Decimal
    updated_at: datetime
    simulated: bool = True

    def __post_init__(self) -> None:
        updated_at = require_utc_aware(self.updated_at)
        if updated_at != self.updated_at:
            object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "symbol", normalize_non_empty(self.symbol, "symbol"))
        object.__setattr__(
            self,
            "quantity",
            normalize_non_negative_decimal(self.quantity, "quantity"),
        )
        object.__setattr__(
            self,
            "unrealized_pnl",
            normalize_decimal(self.unrealized_pnl, "unrealized_pnl"),
        )
        if self.side is PositionSide.FLAT:
            object.__setattr__(self, "quantity", Decimal("0"))
            object.__setattr__(self, "average_entry_price", None)
        if self.quantity == 0 and self.side is not PositionSide.FLAT:
            object.__setattr__(self, "side", PositionSide.FLAT)
            object.__setattr__(self, "average_entry_price", None)
        if self.side is not PositionSide.FLAT and self.average_entry_price is None:
            from trading_framework.core.exceptions import ValidationError

            msg = "non-flat paper position requires average_entry_price"
            raise ValidationError(msg)
        if not self.simulated:
            from trading_framework.core.exceptions import ValidationError

            msg = "PaperPosition must be marked simulated"
            raise ValidationError(msg)
