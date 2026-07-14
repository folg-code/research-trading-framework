"""Futures contract identity helpers."""

from __future__ import annotations

import re

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier

_CONTRACT_CODE_PATTERN = re.compile(r"^[A-Z]{1,4}[FGHJKMNQUVXZ]\d$")
_PRODUCT_PATTERN = re.compile(r"^[A-Z]{1,4}$")


def validate_product_code(product: str) -> str:
    """Return a normalized root product code (e.g. ``NQ``)."""
    normalized = product.strip().upper()
    if not _PRODUCT_PATTERN.fullmatch(normalized):
        msg = f"invalid futures product code: {product!r}"
        raise ValidationError(msg)
    return normalized


def validate_contract_code(contract_code: str) -> str:
    """Return a normalized CME outright contract code (e.g. ``NQM5``)."""
    normalized = contract_code.strip().upper()
    if not _CONTRACT_CODE_PATTERN.fullmatch(normalized):
        msg = f"invalid futures contract code: {contract_code!r}"
        raise ValidationError(msg)
    return normalized


def contract_instrument_id(*, product: str, contract_code: str) -> Identifier:
    """Build a framework instrument id for one outright contract."""
    normalized_product = validate_product_code(product)
    normalized_contract = validate_contract_code(contract_code)
    if not normalized_contract.startswith(normalized_product):
        msg = (
            f"contract code {normalized_contract!r} must start with product {normalized_product!r}"
        )
        raise ValidationError(msg)
    return Identifier(f"{normalized_product}.{normalized_contract}")


def is_outright_contract_symbol(symbol: str, *, product: str) -> bool:
    """Return whether ``symbol`` is an outright contract for ``product``."""
    normalized_product = validate_product_code(product)
    normalized_symbol = symbol.strip().upper()
    if "-" in normalized_symbol:
        return False
    if not normalized_symbol.startswith(normalized_product):
        return False
    return _CONTRACT_CODE_PATTERN.fullmatch(normalized_symbol) is not None


def parse_outright_contract_symbol(symbol: str, *, product: str) -> str | None:
    """Return the contract code when ``symbol`` is an outright ``product`` future."""
    if not is_outright_contract_symbol(symbol, product=product):
        return None
    return validate_contract_code(symbol.strip().upper())
