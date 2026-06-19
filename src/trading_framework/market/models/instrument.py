"""Instrument domain model."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier

_MAX_METADATA_ITEMS = 16


class AssetClass(StrEnum):
    """Supported asset classes for MVP market data."""

    FUTURES = "futures"
    EQUITY = "equity"
    CRYPTO = "crypto"
    FX = "fx"


@final
@dataclass(frozen=True, slots=True)
class Instrument:
    """Provider-independent tradable instrument identity."""

    instrument_id: Identifier
    symbol: str
    asset_class: AssetClass
    exchange: str | None = None
    metadata: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip()
        if not normalized_symbol:
            msg = "symbol must be non-empty"
            raise ValidationError(msg)
        if normalized_symbol != self.symbol:
            object.__setattr__(self, "symbol", normalized_symbol)

        if self.exchange is not None:
            normalized_exchange = self.exchange.strip()
            if not normalized_exchange:
                msg = "exchange must be non-empty when provided"
                raise ValidationError(msg)
            if normalized_exchange != self.exchange:
                object.__setattr__(self, "exchange", normalized_exchange)

        if self.metadata is not None:
            if len(self.metadata) > _MAX_METADATA_ITEMS:
                msg = f"metadata must contain at most {_MAX_METADATA_ITEMS} items"
                raise ValidationError(msg)
            for key, value in self.metadata.items():
                if not key.strip():
                    msg = "metadata keys must be non-empty"
                    raise ValidationError(msg)
                if not value.strip():
                    msg = "metadata values must be non-empty"
                    raise ValidationError(msg)
