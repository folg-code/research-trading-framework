"""Instrument domain model tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.models import AssetClass, Instrument


def test_instrument_stores_core_fields() -> None:
    instrument = Instrument(
        instrument_id=Identifier("ES.c.0"),
        symbol="ES",
        asset_class=AssetClass.FUTURES,
        exchange="CME",
    )
    assert instrument.symbol == "ES"
    assert instrument.asset_class is AssetClass.FUTURES
    assert instrument.exchange == "CME"


def test_instrument_normalizes_symbol_whitespace() -> None:
    instrument = Instrument(
        instrument_id=Identifier("btc-usd"),
        symbol="  BTCUSD  ",
        asset_class=AssetClass.CRYPTO,
    )
    assert instrument.symbol == "BTCUSD"


def test_instrument_accepts_bounded_metadata() -> None:
    instrument = Instrument(
        instrument_id=Identifier("AAPL"),
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        metadata={"sector": "technology"},
    )
    assert instrument.metadata == {"sector": "technology"}


def test_instrument_rejects_empty_symbol() -> None:
    with pytest.raises(ValidationError):
        Instrument(
            instrument_id=Identifier("bad"),
            symbol="   ",
            asset_class=AssetClass.EQUITY,
        )
