"""CSV file inspector for OHLCV import configuration."""

import csv
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.importers import (
    DetectedFileFormat,
    FileInspectionResult,
)

_TIMESTAMP_COLUMN_NAMES = frozenset(
    {
        "timestamp",
        "time",
        "datetime",
        "date",
        "ts",
        "observed_at",
        "bar_time",
    }
)
_ENCODINGS_TO_TRY = ("utf-8-sig", "utf-8")


def _detect_timestamp_candidates(columns: tuple[str, ...]) -> tuple[str, ...]:
    candidates = [column for column in columns if column.strip().lower() in _TIMESTAMP_COLUMN_NAMES]
    return tuple(candidates)


def _read_header(path: Path) -> tuple[tuple[str, ...], str]:
    last_error: ValidationError | None = None
    for encoding in _ENCODINGS_TO_TRY:
        try:
            with path.open(encoding=encoding, newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, None)
        except UnicodeDecodeError as exc:
            last_error = ValidationError(f"unable to decode CSV file: {path}")
            last_error.__cause__ = exc
            continue
        except OSError as exc:
            msg = f"unable to read CSV file: {path}"
            raise ValidationError(msg) from exc

        if header is None:
            msg = f"CSV file has no header row: {path}"
            raise ValidationError(msg)
        columns = tuple(column.strip() for column in header if column.strip())
        if not columns:
            msg = f"CSV header contains no columns: {path}"
            raise ValidationError(msg)
        return columns, encoding

    if last_error is not None:
        raise last_error
    msg = f"unable to decode CSV file: {path}"
    raise ValidationError(msg)


def _estimate_row_count(path: Path, encoding: str) -> int:
    try:
        with path.open(encoding=encoding, newline="") as handle:
            row_count = sum(1 for _ in handle)
    except OSError as exc:
        msg = f"unable to read CSV file: {path}"
        raise ValidationError(msg) from exc
    return max(row_count - 1, 0)


class CsvFileInspector:
    """Inspect CSV files for OHLCV import without loading full datasets."""

    def inspect(self, path: Path) -> FileInspectionResult:
        """Return structural metadata for configuring CSV OHLCV import."""
        if not path.exists():
            msg = f"file does not exist: {path}"
            raise ValidationError(msg)
        if not path.is_file():
            msg = f"path is not a file: {path}"
            raise ValidationError(msg)

        suffix = path.suffix.lower()
        detected_format = DetectedFileFormat.CSV if suffix == ".csv" else DetectedFileFormat.UNKNOWN

        columns, encoding = _read_header(path)
        timestamp_candidates = _detect_timestamp_candidates(columns)
        row_estimate = _estimate_row_count(path, encoding)

        return FileInspectionResult(
            path=path,
            format=detected_format,
            columns=columns,
            row_estimate=row_estimate,
            timestamp_column_candidates=timestamp_candidates,
            encoding=encoding,
        )
