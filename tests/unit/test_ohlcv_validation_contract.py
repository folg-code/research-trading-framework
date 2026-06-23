"""OHLCV validation contract tests."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market.validation import (
    OhlcvValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class _StubOhlcvValidator:
    def validate(self, bars: Sequence[MarketBar]) -> ValidationResult:
        if not bars:
            return ValidationResult(
                issues=(
                    ValidationIssue(
                        message="dataset is empty",
                        severity=ValidationSeverity.ERROR,
                    ),
                )
            )
        return ValidationResult(issues=())


def _sample_bar() -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_validation_result_serializes_issues() -> None:
    result = ValidationResult(
        issues=(
            ValidationIssue(
                message="duplicate timestamp",
                severity=ValidationSeverity.ERROR,
                row_number=3,
                field="observed_at",
            ),
        )
    )
    payload = result.to_dict()
    assert payload["is_valid"] is False
    assert payload["issues"][0]["field"] == "observed_at"


def test_ohlcv_validator_protocol_is_implementable() -> None:
    validator: OhlcvValidator = _StubOhlcvValidator()
    assert validator.validate([_sample_bar()]).is_valid is True
