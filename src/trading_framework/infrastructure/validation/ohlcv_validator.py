"""OHLCV batch validator."""

from collections.abc import Sequence

from trading_framework.market.models import MarketBar
from trading_framework.market.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

_REQUIRED_FIELDS = ("open", "high", "low", "close", "volume", "observed_at", "available_at")


class OhlcvBarValidator:
    """Validate batches of materialized OHLCV bars."""

    def validate(self, bars: Sequence[MarketBar]) -> ValidationResult:
        """Validate ordering, duplicates and bar invariants for a batch."""
        issues: list[ValidationIssue] = []

        if not bars:
            issues.append(
                ValidationIssue(
                    message="dataset is empty",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(issues=tuple(issues))

        seen_observed_at: set[object] = set()
        previous_observed_at = bars[0].observed_at

        for index, bar in enumerate(bars, start=1):
            for field in _REQUIRED_FIELDS:
                if getattr(bar, field) is None:
                    issues.append(
                        ValidationIssue(
                            message=f"missing required field: {field}",
                            severity=ValidationSeverity.ERROR,
                            row_number=index,
                            field=field,
                        )
                    )

            if bar.volume.value < 0:
                issues.append(
                    ValidationIssue(
                        message="volume must be non-negative",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="volume",
                    )
                )

            observed_key = bar.observed_at
            if observed_key in seen_observed_at:
                issues.append(
                    ValidationIssue(
                        message="duplicate observed_at timestamp",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="observed_at",
                    )
                )
            seen_observed_at.add(observed_key)

            if index > 1 and bar.observed_at < previous_observed_at:
                issues.append(
                    ValidationIssue(
                        message="timestamps must be in non-decreasing order",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="observed_at",
                    )
                )
            previous_observed_at = bar.observed_at

        return ValidationResult(issues=tuple(issues))
