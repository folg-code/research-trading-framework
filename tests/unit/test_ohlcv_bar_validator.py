"""OHLCV validator implementation tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.validation import OhlcvBarValidator
from trading_framework.market.models import MarketBar
from trading_framework.market.validation import OhlcvValidator, ValidationSeverity


def _bar(minute: int, *, volume: int = 1000) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(volume),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_ohlcv_bar_validator_accepts_valid_batch() -> None:
    result = OhlcvBarValidator().validate([_bar(0), _bar(1)])
    assert result.is_valid is True


def test_ohlcv_bar_validator_rejects_empty_batch() -> None:
    result = OhlcvBarValidator().validate([])
    assert result.is_valid is False
    assert result.issues[0].message == "dataset is empty"


def test_ohlcv_bar_validator_detects_duplicate_timestamps() -> None:
    result = OhlcvBarValidator().validate([_bar(0), _bar(0)])
    assert result.is_valid is False
    assert any(issue.field == "observed_at" for issue in result.issues)


def test_ohlcv_bar_validator_detects_out_of_order_timestamps() -> None:
    result = OhlcvBarValidator().validate([_bar(1), _bar(0)])
    assert result.is_valid is False
    assert result.issues[0].severity is ValidationSeverity.ERROR


def test_ohlcv_bar_validator_satisfies_protocol() -> None:
    validator: OhlcvValidator = OhlcvBarValidator()
    assert validator.validate([_bar(0)]).is_valid is True
