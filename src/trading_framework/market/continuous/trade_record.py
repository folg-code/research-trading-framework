"""Continuous-layer trade storage record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.contracts.identity import (
    validate_contract_code,
    validate_product_code,
)
from trading_framework.market.models import MarketTrade

MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION = "market-trade-continuous-v1"


@final
@dataclass(frozen=True, slots=True)
class ContinuousTradeRecord:
    """Persisted continuous trade row with roll lineage fields."""

    trade: MarketTrade
    actual_contract: str
    product: str
    session_date: date
    continuous_symbol: str
    roll_id: str
    is_roll_boundary: bool

    def __post_init__(self) -> None:
        normalized_product = validate_product_code(self.product)
        normalized_contract = validate_contract_code(self.actual_contract)
        if normalized_product != self.product:
            object.__setattr__(self, "product", normalized_product)
        if normalized_contract != self.actual_contract:
            object.__setattr__(self, "actual_contract", normalized_contract)
        if not self.continuous_symbol.strip():
            msg = "continuous_symbol must be non-empty"
            raise ValidationError(msg)
        if not self.roll_id.strip():
            msg = "roll_id must be non-empty"
            raise ValidationError(msg)
