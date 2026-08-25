"""OHLCV table validator for Arrow batches."""

from __future__ import annotations

import numpy as np
import pyarrow as pa
from numpy.typing import NDArray

from trading_framework.infrastructure.storage.parquet.writer import MARKET_BAR_PARQUET_SCHEMA
from trading_framework.market.validation import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ohlc_invariant_issues,
)

_REQUIRED_FIELDS = ("open", "high", "low", "close", "volume", "observed_at", "available_at")


class OhlcvTableValidator:
    """Validate canonical OHLCV Arrow tables without materializing ``MarketBar``."""

    def validate_table(self, table: pa.Table) -> ValidationResult:
        """Validate emptiness, required fields, order, volume, and OHLC invariants."""
        issues: list[ValidationIssue] = []
        if table.num_rows == 0:
            issues.append(
                ValidationIssue(
                    message="dataset is empty",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(issues=tuple(issues))

        missing_columns = [field for field in _REQUIRED_FIELDS if field not in table.column_names]
        if missing_columns:
            for field in missing_columns:
                issues.append(
                    ValidationIssue(
                        message=f"missing required field: {field}",
                        severity=ValidationSeverity.ERROR,
                        field=field,
                    )
                )
            return ValidationResult(issues=tuple(issues))

        normalized = table.select(_REQUIRED_FIELDS).cast(MARKET_BAR_PARQUET_SCHEMA, safe=False)
        for field in _REQUIRED_FIELDS:
            null_mask = np.asarray(normalized.column(field).is_null().to_numpy(), dtype=bool)
            for index in np.flatnonzero(null_mask):
                issues.append(
                    ValidationIssue(
                        message=f"missing required field: {field}",
                        severity=ValidationSeverity.ERROR,
                        row_number=int(index) + 1,
                        field=field,
                    )
                )

        volumes = np.asarray(
            normalized.column("volume").fill_null(0).to_numpy(),
            dtype=np.int64,
        )
        for index in np.flatnonzero(volumes < 0):
            issues.append(
                ValidationIssue(
                    message="volume must be non-negative",
                    severity=ValidationSeverity.ERROR,
                    row_number=int(index) + 1,
                    field="volume",
                )
            )

        observed = normalized.column("observed_at").to_pylist()
        available = normalized.column("available_at").to_pylist()
        seen_observed_at: set[object] = set()
        previous_observed_at = observed[0]
        for row_number, timestamp in enumerate(observed, start=1):
            if timestamp in seen_observed_at:
                issues.append(
                    ValidationIssue(
                        message="duplicate observed_at timestamp",
                        severity=ValidationSeverity.ERROR,
                        row_number=row_number,
                        field="observed_at",
                    )
                )
            seen_observed_at.add(timestamp)
            if (
                row_number > 1
                and timestamp is not None
                and previous_observed_at is not None
                and timestamp < previous_observed_at
            ):
                issues.append(
                    ValidationIssue(
                        message="timestamps must be in non-decreasing order",
                        severity=ValidationSeverity.ERROR,
                        row_number=row_number,
                        field="observed_at",
                    )
                )
            previous_observed_at = timestamp
            available_at = available[row_number - 1]
            if timestamp is not None and available_at is not None and available_at <= timestamp:
                issues.append(
                    ValidationIssue(
                        message="available_at must be after observed_at",
                        severity=ValidationSeverity.ERROR,
                        row_number=row_number,
                        field="available_at",
                    )
                )

        open_values = _float_price_column(normalized, "open")
        high_values = _float_price_column(normalized, "high")
        low_values = _float_price_column(normalized, "low")
        close_values = _float_price_column(normalized, "close")
        issues.extend(
            ohlc_invariant_issues(
                open=open_values,
                high=high_values,
                low=low_values,
                close=close_values,
            )
        )
        return ValidationResult(issues=tuple(issues))


def _float_price_column(table: pa.Table, name: str) -> NDArray[np.float64]:
    casted = table.column(name).cast(pa.float64(), safe=False)
    return np.asarray(casted.to_numpy(zero_copy_only=False), dtype=np.float64)
