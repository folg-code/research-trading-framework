"""Market trade batch validator."""

from collections.abc import Sequence

import numpy as np

from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
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

    def validate_storage_columns(self, columns: ContractChunkColumns) -> ValidationResult:
        """Validate ordering and invariants for batch column buffers."""
        issues: list[ValidationIssue] = []

        if len(columns) == 0:
            issues.append(
                ValidationIssue(
                    message="dataset is empty",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(issues=tuple(issues))

        price_nanos = np.asarray(columns.price_nanos, dtype=np.int64)
        if np.any(price_nanos <= 0):
            first_invalid = int(np.argmax(price_nanos <= 0)) + 1
            issues.append(
                ValidationIssue(
                    message="price must be positive",
                    severity=ValidationSeverity.ERROR,
                    row_number=first_invalid,
                    field="price_nanos",
                )
            )

        ts_event_ns = np.asarray(columns.ts_event_ns, dtype=np.int64)
        if ts_event_ns.size > 1 and np.any(np.diff(ts_event_ns) < 0):
            first_decrease = int(np.argmax(np.diff(ts_event_ns) < 0)) + 2
            issues.append(
                ValidationIssue(
                    message="timestamps must be in non-decreasing order",
                    severity=ValidationSeverity.ERROR,
                    row_number=first_decrease,
                    field="ts_event_ns",
                )
            )

        return ValidationResult(issues=tuple(issues))

    def validate_records(self, records: Sequence[ContractTradeRecord]) -> ValidationResult:
        """Validate ordering and invariants for storage-ready contract records."""
        issues: list[ValidationIssue] = []

        if not records:
            issues.append(
                ValidationIssue(
                    message="dataset is empty",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(issues=tuple(issues))

        previous_ts_event_ns = records[0].ts_event_ns
        for index, record in enumerate(records, start=1):
            if record.price_nanos <= 0:
                issues.append(
                    ValidationIssue(
                        message="price must be positive",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="price_nanos",
                    )
                )
            if index > 1 and record.ts_event_ns < previous_ts_event_ns:
                issues.append(
                    ValidationIssue(
                        message="timestamps must be in non-decreasing order",
                        severity=ValidationSeverity.ERROR,
                        row_number=index,
                        field="ts_event_ns",
                    )
                )
            previous_ts_event_ns = record.ts_event_ns

        return ValidationResult(issues=tuple(issues))
