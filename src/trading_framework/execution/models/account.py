"""Paper account contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import final

from trading_framework.execution.models._validation import (
    normalize_decimal,
    normalize_non_empty,
    normalize_non_negative_decimal,
)
from trading_framework.time.models.utc_instant import require_utc_aware


@final
@dataclass(frozen=True, slots=True)
class PaperAccountSnapshot:
    """Paper account equity snapshot for dry-run reporting."""

    account_id: str
    currency: str
    starting_equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal
    updated_at: datetime
    simulated: bool = True

    def __post_init__(self) -> None:
        updated_at = require_utc_aware(self.updated_at)
        if updated_at != self.updated_at:
            object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "account_id", normalize_non_empty(self.account_id, "account_id"))
        object.__setattr__(self, "currency", normalize_non_empty(self.currency, "currency"))
        object.__setattr__(
            self,
            "starting_equity",
            normalize_non_negative_decimal(self.starting_equity, "starting_equity"),
        )
        object.__setattr__(
            self,
            "realized_pnl",
            normalize_decimal(self.realized_pnl, "realized_pnl"),
        )
        object.__setattr__(
            self,
            "unrealized_pnl",
            normalize_decimal(self.unrealized_pnl, "unrealized_pnl"),
        )
        object.__setattr__(self, "equity", normalize_non_negative_decimal(self.equity, "equity"))
        if not self.simulated:
            from trading_framework.core.exceptions import ValidationError

            msg = "PaperAccountSnapshot must be marked simulated"
            raise ValidationError(msg)
