"""MVP numeric type tests."""

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume


def test_price_accepts_decimal_value() -> None:
    price = Price(Decimal("101.25"))
    assert price.value == Decimal("101.25")
    assert price.to_json() == "101.25"


def test_price_parses_from_json_string() -> None:
    price = Price.from_json("42.5")
    assert price.value == Decimal("42.5")


def test_price_rejects_non_finite_value() -> None:
    with pytest.raises(ValidationError):
        Price(Decimal("NaN"))


def test_volume_accepts_non_negative_integer() -> None:
    volume = Volume(1_000)
    assert volume.to_json() == 1_000


def test_volume_rejects_negative_value() -> None:
    with pytest.raises(ValidationError):
        Volume(-1)
