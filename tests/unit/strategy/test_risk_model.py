"""Unit tests for Risk Model contracts."""

from __future__ import annotations

from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.strategy.risk_model import (
    EquityPercentRiskModel,
    FixedQuantityRiskModel,
)


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


# ---------------------------------------------------------------------------
# EquityPercentRiskModel — STATIC, authoring-time sizing (D-S048-05).
#
# This is resolved once at construction from author-supplied values; it is
# never dynamic, compounding, or equity-curve-following sizing.
# ---------------------------------------------------------------------------


def test_equity_percent_risk_model_derives_quantity_once_at_construction() -> None:
    # Hand-computed: 100_000 * 0.01 / 50 == 20
    model = EquityPercentRiskModel(
        account_equity=Decimal("100000"),
        risk_percent=Decimal("0.01"),
        stop_distance=Decimal("50"),
    )
    assert model.quantity == Decimal("20")
    assert model.position_quantity() == Decimal("20")
    # Calling position_quantity() repeatedly returns the same stored value
    # (resolved once at authoring time, not recomputed per call).
    assert model.position_quantity() is model.position_quantity()


def test_equity_percent_risk_model_hand_computed_decimal_rounding_case() -> None:
    # Hand-computed: 10_000 * 0.015 / 7 == 150 / 7 == 21.428571428571428571428571429
    # (Decimal default context precision is 28 significant digits).
    model = EquityPercentRiskModel(
        account_equity=Decimal("10000"),
        risk_percent=Decimal("0.015"),
        stop_distance=Decimal("7"),
    )
    expected = Decimal("10000") * Decimal("0.015") / Decimal("7")
    assert expected == Decimal("21.42857142857142857142857143")
    assert model.quantity == expected


def test_equity_percent_risk_model_position_quantity_matches_derivation() -> None:
    model = EquityPercentRiskModel(
        account_equity=Decimal("50000"),
        risk_percent=Decimal("0.02"),
        stop_distance=Decimal("25"),
    )
    # Hand-computed: 50_000 * 0.02 / 25 == 40
    assert model.position_quantity() == Decimal("40")


def test_equity_percent_risk_model_allows_entry_when_flat() -> None:
    model = EquityPercentRiskModel(
        account_equity=Decimal("100000"),
        risk_percent=Decimal("0.01"),
        stop_distance=Decimal("50"),
    )
    assert model.allows_new_entry(open_position_count=0) is True
    assert model.allows_new_entry(open_position_count=1) is False


def test_equity_percent_risk_model_rejects_non_positive_account_equity() -> None:
    with pytest.raises(ValidationError, match="account_equity"):
        EquityPercentRiskModel(
            account_equity=Decimal("0"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("50"),
        )


def test_equity_percent_risk_model_rejects_risk_percent_above_one() -> None:
    with pytest.raises(ValidationError, match="risk_percent"):
        EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("1.5"),
            stop_distance=Decimal("50"),
        )


def test_equity_percent_risk_model_rejects_zero_risk_percent() -> None:
    with pytest.raises(ValidationError, match="risk_percent"):
        EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("0"),
            stop_distance=Decimal("50"),
        )


def test_equity_percent_risk_model_rejects_non_positive_stop_distance() -> None:
    with pytest.raises(ValidationError, match="stop_distance"):
        EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("0"),
        )


def test_equity_percent_risk_model_rejects_negative_stop_distance() -> None:
    with pytest.raises(ValidationError, match="stop_distance"):
        EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("-10"),
        )


def test_equity_percent_risk_model_rejects_derived_zero_quantity() -> None:
    # account_equity is small enough that account_equity * risk_percent
    # underflows to an exact Decimal 0 (below the context's Etiny), so the
    # derived quantity is 0 even though every individual field is positive.
    with pytest.raises(ValidationError, match="quantity"):
        EquityPercentRiskModel(
            account_equity=Decimal("1e-9000000"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("50"),
        )


def test_equity_percent_risk_model_rejects_max_positions_below_one() -> None:
    with pytest.raises(ValidationError, match="max_positions"):
        EquityPercentRiskModel(
            account_equity=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            stop_distance=Decimal("50"),
            max_positions=0,
        )
