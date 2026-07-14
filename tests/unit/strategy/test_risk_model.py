"""Unit tests for Risk Model contracts."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.strategy.risk_model import FixedQuantityRiskModel


def test_fixed_quantity_risk_model_allows_entry_when_flat() -> None:
    model = FixedQuantityRiskModel(quantity=Decimal("1"))
    assert model.allows_new_entry(open_position_count=0) is True
    assert model.allows_new_entry(open_position_count=1) is False


def test_fixed_quantity_risk_model_position_quantity() -> None:
    model = FixedQuantityRiskModel(quantity=Decimal("2.5"))
    assert model.position_quantity() == Decimal("2.5")


def test_fixed_quantity_risk_model_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValidationError, match="quantity"):
        FixedQuantityRiskModel(quantity=Decimal("0"))
