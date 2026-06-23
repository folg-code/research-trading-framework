"""OHLCV validation contracts."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from trading_framework.market.models import MarketBar


class ValidationSeverity(StrEnum):
    """Severity of a validation issue."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single validation issue for a dataset or row."""

    message: str
    severity: ValidationSeverity
    row_number: int | None = None
    field: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Explicit validation outcome for OHLCV data."""

    issues: tuple[ValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Return whether the dataset passed validation."""
        return not any(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the validation result to a JSON-compatible dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [
                {
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "row_number": issue.row_number,
                    "field": issue.field,
                }
                for issue in self.issues
            ],
        }


class OhlcvValidator(Protocol):
    """Validate normalized or materialized OHLCV bars."""

    def validate(self, bars: Sequence[MarketBar]) -> ValidationResult:
        """Validate a batch of market bars."""
