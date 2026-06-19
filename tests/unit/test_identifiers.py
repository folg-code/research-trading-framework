"""Identifier value object tests."""

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier


def test_identifier_stores_normalized_value() -> None:
    identifier = Identifier("  dataset-1  ")
    assert identifier.value == "dataset-1"
    assert str(identifier) == "dataset-1"


def test_identifier_equality_and_hashing() -> None:
    left = Identifier("abc")
    right = Identifier("abc")
    assert left == right
    assert hash(left) == hash(right)


def test_empty_identifier_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Identifier("   ")
