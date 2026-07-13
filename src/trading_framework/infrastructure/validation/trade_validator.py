"""Market trade batch validator."""

from collections.abc import Sequence

from trading_framework.market.models.trade import MarketTrade
from trading_framework.market.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TradeBatchValidator:
    """Validate batches of materialized market trades."""

    def validate(self, trades: Sequence[MarketTrade]) -> ValidationResult:
        """Validate ordering and trade invariants for a batch."""
        issues: list[ValidationIssue] = []

        if not trades:
            issues.append(
                ValidationIssue(
                    message="dataset is empty",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(issues=tuple(issues))

        previous_event_at = trades[0].event_at
        for index, trade in enumerate(trades, start=1):
            if trade.price.value <= 0:
                issues.append(
                    ValidationIssue(
                        message="price must be positive",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="price",
                    )
                )

            if index > 1 and trade.event_at < previous_event_at:
                issues.append(
                    ValidationIssue(
                        message="timestamps must be in non-decreasing order",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="event_at",
                    )
                )
            previous_event_at = trade.event_at

        return ValidationResult(issues=tuple(issues))
