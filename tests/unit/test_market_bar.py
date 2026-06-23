"""MarketBar domain model tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar


def _bar(
    *,
    open_: str = "100",
    high: str = "105",
    low: str = "99",
    close: str = "103",
    volume: int = 1000,
) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal(open_)),
        high=Price(Decimal(high)),
        low=Price(Decimal(low)),
        close=Price(Decimal(close)),
        volume=Volume(volume),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_market_bar_accepts_valid_values() -> None:
    bar = _bar()
    assert bar.close.value == Decimal("103")
    assert bar.volume.value == 1000


def test_market_bar_rejects_invalid_high() -> None:
    with pytest.raises(ValidationError):
        _bar(high="90")


def test_market_bar_rejects_non_utc_observed_at() -> None:
    with pytest.raises(ValidationError):
        MarketBar(
            open=Price(Decimal("100")),
            high=Price(Decimal("101")),
            low=Price(Decimal("99")),
            close=Price(Decimal("100")),
            volume=Volume(10),
            observed_at=datetime(2024, 1, 1, 12, 0),
            available_at=datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
        )
