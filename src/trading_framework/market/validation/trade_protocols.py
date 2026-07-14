"""Trade validation contracts."""

from collections.abc import Sequence
from typing import Protocol

from trading_framework.market.models.trade import MarketTrade
from trading_framework.market.validation.protocols import ValidationResult


class TradeValidator(Protocol):
    """Validate materialized market trades."""

    def validate(self, trades: Sequence[MarketTrade]) -> ValidationResult:
        """Validate a batch of market trades."""
