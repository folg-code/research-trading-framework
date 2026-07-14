"""Instrument identity cache for Databento contract decode."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.market.contracts.identity import (
    parse_outright_contract_symbol,
    validate_contract_code,
    validate_product_code,
)


@dataclass(frozen=True, slots=True)
class InstrumentIdentity:
    """Pre-validated product and contract identity for one instrument."""

    product: str
    contract_code: str


class InstrumentIdentityCache:
    """Cache instrument_id and symbol lookups during one archive decode."""

    def __init__(self, *, product: str) -> None:
        self._product = product
        self._validated_product = validate_product_code(product)
        self._by_symbol: dict[str, InstrumentIdentity | None] = {}
        self._by_instrument_id: dict[int, InstrumentIdentity | None] = {}

    def resolve(
        self,
        *,
        symbol: str,
        instrument_id: int | None = None,
    ) -> InstrumentIdentity | None:
        """Return pre-validated identity for one symbol/instrument pair."""
        if instrument_id is not None and instrument_id in self._by_instrument_id:
            return self._by_instrument_id[instrument_id]

        if symbol in self._by_symbol:
            identity = self._by_symbol[symbol]
        else:
            contract_code = parse_outright_contract_symbol(symbol, product=self._product)
            if contract_code is None:
                identity = None
            else:
                identity = InstrumentIdentity(
                    product=self._validated_product,
                    contract_code=validate_contract_code(contract_code),
                )
            self._by_symbol[symbol] = identity

        if instrument_id is not None:
            self._by_instrument_id[instrument_id] = identity
        return identity
