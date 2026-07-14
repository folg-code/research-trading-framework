"""Futures contract identity tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.contracts.identity import (
    contract_instrument_id,
    is_outright_contract_symbol,
    parse_outright_contract_symbol,
)


def test_contract_instrument_id_builds_product_contract_identifier() -> None:
    assert contract_instrument_id(product="NQ", contract_code="NQM5").value == "NQ.NQM5"


@pytest.mark.parametrize(
    ("symbol", "expected"),
    [
        ("NQU5", True),
        ("NQZ5", True),
        ("NQU5-NQZ5", False),
        ("ESU5", False),
        ("NQ.FUT", False),
    ],
)
def test_is_outright_contract_symbol_for_nq(symbol: str, expected: bool) -> None:
    assert is_outright_contract_symbol(symbol, product="NQ") is expected


def test_parse_outright_contract_symbol_returns_none_for_spread() -> None:
    assert parse_outright_contract_symbol("NQU5-NQZ5", product="NQ") is None


def test_validate_contract_code_rejects_invalid_symbol() -> None:
    with pytest.raises(ValidationError):
        contract_instrument_id(product="NQ", contract_code="NQ.FUT")
