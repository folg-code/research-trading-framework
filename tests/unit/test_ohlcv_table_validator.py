"""OHLCV Arrow table validator tests."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pyarrow as pa

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.writer import (
    MARKET_BAR_PARQUET_SCHEMA,
    market_bars_to_table,
)
from trading_framework.infrastructure.validation import OhlcvBarValidator, OhlcvTableValidator
from trading_framework.market.models import MarketBar
from trading_framework.market.validation import ValidationResult, ValidationSeverity


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


def _issue_keys(result: ValidationResult) -> list[tuple[str, int | None, str | None]]:
    return [(issue.message, issue.row_number, issue.field) for issue in result.issues]


def test_ohlcv_table_validator_matches_bar_validator_on_valid_and_order_issues() -> None:
    bar_validator = OhlcvBarValidator()
    table_validator = OhlcvTableValidator()
    valid_bars = [_bar(0), _bar(1)]
    duplicate_bars = [_bar(0), _bar(0)]
    unordered_bars = [_bar(1), _bar(0)]

    for bars in (valid_bars, duplicate_bars, unordered_bars, []):
        bar_result = bar_validator.validate(bars)
        table_result = table_validator.validate_table(market_bars_to_table(bars))
        assert bar_result.is_valid is table_result.is_valid
        assert _issue_keys(bar_result) == _issue_keys(table_result)


def test_ohlcv_table_validator_accepts_valid_table() -> None:
    result = OhlcvTableValidator().validate_table(market_bars_to_table([_bar(0), _bar(1)]))
    assert result.is_valid is True


def test_ohlcv_table_validator_rejects_empty_table() -> None:
    result = OhlcvTableValidator().validate_table(market_bars_to_table([]))
    assert result.is_valid is False
    assert result.issues[0].message == "dataset is empty"
    assert result.issues[0].severity is ValidationSeverity.ERROR


def test_ohlcv_table_validator_detects_negative_volume() -> None:
    table = pa.table(
        {
            "open": ["100"],
            "high": ["101"],
            "low": ["99"],
            "close": ["100"],
            "volume": [-1],
            "observed_at": [datetime(2024, 1, 1, 12, 0)],
            "available_at": [datetime(2024, 1, 1, 12, 1)],
        },
        schema=MARKET_BAR_PARQUET_SCHEMA,
    )
    result = OhlcvTableValidator().validate_table(table)
    assert result.is_valid is False
    assert any(issue.field == "volume" for issue in result.issues)


def test_ohlcv_table_validator_detects_invalid_ohlc() -> None:
    table = pa.table(
        {
            "open": ["100"],
            "high": ["99"],
            "low": ["98"],
            "close": ["99.5"],
            "volume": [10],
            "observed_at": [datetime(2024, 1, 1, 12, 0)],
            "available_at": [datetime(2024, 1, 1, 12, 1)],
        },
        schema=MARKET_BAR_PARQUET_SCHEMA,
    )
    result = OhlcvTableValidator().validate_table(table)
    assert result.is_valid is False
    assert any(issue.message == "high must be >= open and close" for issue in result.issues)


def test_ohlcv_table_validator_detects_available_at_not_after_observed() -> None:
    observed = datetime(2024, 1, 1, 12, 0)
    table = pa.table(
        {
            "open": ["100"],
            "high": ["101"],
            "low": ["99"],
            "close": ["100"],
            "volume": [10],
            "observed_at": [observed],
            "available_at": [observed],
        },
        schema=MARKET_BAR_PARQUET_SCHEMA,
    )
    result = OhlcvTableValidator().validate_table(table)
    assert result.is_valid is False
    assert any(issue.field == "available_at" for issue in result.issues)
