"""Continuous futures instrument identity helpers."""

from __future__ import annotations

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.contracts.identity import validate_product_code

CONTINUOUS_TRADES_PROVIDER = "continuous"
CONTINUOUS_BUILDER_VERSION = "continuous-trades-builder-v1"


def continuous_instrument_id(product: str) -> Identifier:
    """Return the materialized continuous instrument id for one product."""
    normalized_product = validate_product_code(product)
    return Identifier(f"{normalized_product}.c.0")


def is_continuous_instrument_id(instrument_id: Identifier) -> bool:
    """Return whether ``instrument_id`` identifies one materialized continuous future."""
    value = instrument_id.value
    parts = value.split(".")
    if len(parts) != 3 or parts[1] != "c" or parts[2] != "0":
        return False
    try:
        validate_product_code(parts[0])
    except ValidationError:
        return False
    return True


def continuous_symbol_label(product: str) -> str:
    """Return the logical continuous symbol label stored on trade rows."""
    return f"{validate_product_code(product)}_CONT"
