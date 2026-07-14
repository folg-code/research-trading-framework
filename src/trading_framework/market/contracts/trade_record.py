"""Contract-layer trade storage record."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.contracts.identity import (
    validate_contract_code,
    validate_product_code,
)
from trading_framework.market.contracts.storage_codec import (
    market_trade_from_storage,
    utc_datetime_from_ns,
)
from trading_framework.market.models import MarketTrade

MARKET_TRADE_CONTRACT_SCHEMA_VERSION = "market-trade-contract-v2"


@final
@dataclass(frozen=True, slots=True)
class ContractTradeRecord:
    """Persisted contract trade row with storage-ready normalized fields."""

    ts_event_ns: int
    ts_recv_ns: int
    price_nanos: int
    size: int
    instrument_id: int
    sequence: int
    publisher_id: int
    side: str | None
    product: str
    contract_code: str
    session_date: date
    source_file: str
    _identity_prevalidated: bool = field(default=False, repr=False, compare=False)

    @property
    def actual_contract(self) -> str:
        """Backward-compatible alias used by roll/materialization code."""
        return self.contract_code

    def event_at(self) -> datetime:
        """Decode canonical event timestamp for domain workflows."""
        return utc_datetime_from_ns(self.ts_event_ns)

    def to_market_trade(self) -> MarketTrade:
        """Materialize a domain trade without re-encoding storage fields."""
        return market_trade_from_storage(
            ts_event_ns=self.ts_event_ns,
            ts_recv_ns=self.ts_recv_ns,
            price_nanos=self.price_nanos,
            size=self.size,
            side=self.side,
            sequence=self.sequence,
        )

    @classmethod
    def from_prevalidated_identity(
        cls,
        *,
        validated_product: str,
        validated_contract_code: str,
        ts_event_ns: int,
        ts_recv_ns: int,
        price_nanos: int,
        size: int,
        instrument_id: int,
        sequence: int,
        publisher_id: int,
        side: str | None,
        session_date: date,
        source_file: str,
    ) -> ContractTradeRecord:
        """Build one record when product/contract were validated once for the batch."""
        return cls(
            ts_event_ns=ts_event_ns,
            ts_recv_ns=ts_recv_ns,
            price_nanos=price_nanos,
            size=size,
            instrument_id=instrument_id,
            sequence=sequence,
            publisher_id=publisher_id,
            side=side,
            product=validated_product,
            contract_code=validated_contract_code,
            session_date=session_date,
            source_file=source_file,
            _identity_prevalidated=True,
        )

    def __post_init__(self) -> None:
        if not self._identity_prevalidated:
            normalized_product = validate_product_code(self.product)
            normalized_contract = validate_contract_code(self.contract_code)
            if normalized_product != self.product:
                object.__setattr__(self, "product", normalized_product)
            if normalized_contract != self.contract_code:
                object.__setattr__(self, "contract_code", normalized_contract)
        if not self.source_file.strip():
            msg = "source_file must be non-empty"
            raise ValidationError(msg)
        if self.ts_event_ns <= 0:
            msg = "ts_event_ns must be positive"
            raise ValidationError(msg)
        if self.ts_recv_ns < 0:
            msg = "ts_recv_ns must be non-negative"
            raise ValidationError(msg)
        if self.price_nanos <= 0:
            msg = "price_nanos must be positive"
            raise ValidationError(msg)
        if self.size <= 0:
            msg = "size must be positive"
            raise ValidationError(msg)
        if self.sequence < 0:
            msg = "sequence must be non-negative"
            raise ValidationError(msg)
