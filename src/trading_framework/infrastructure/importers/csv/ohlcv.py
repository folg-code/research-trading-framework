"""Streaming CSV OHLCV importer."""

import csv
from collections.abc import Iterator
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.importers.csv.inspector import CsvFileInspector
from trading_framework.infrastructure.normalization import UtcOhlcvNormalizer
from trading_framework.market.importers import FileInspector
from trading_framework.market.normalization import (
    NormalizedBarRow,
    OhlcvImportConfig,
    OhlcvNormalizer,
)


class CsvOhlcvImporter:
    """Stream normalized OHLCV rows from an external CSV file."""

    def __init__(
        self,
        inspector: FileInspector | None = None,
        normalizer: OhlcvNormalizer | None = None,
    ) -> None:
        self._inspector = inspector or CsvFileInspector()
        self._normalizer = normalizer or UtcOhlcvNormalizer()

    def iter_rows(self, path: Path, config: OhlcvImportConfig) -> Iterator[NormalizedBarRow]:
        """Yield normalized rows without loading the full file into memory."""
        inspection = self._inspector.inspect(path)
        if inspection.format.value != "csv":
            msg = f"unsupported file format for CSV import: {inspection.format.value}"
            raise ValidationError(msg)

        encoding = inspection.encoding or "utf-8"
        try:
            handle = path.open(encoding=encoding, newline="")
        except OSError as exc:
            msg = f"unable to read CSV file: {path}"
            raise ValidationError(msg) from exc

        with handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                msg = f"CSV file has no header row: {path}"
                raise ValidationError(msg)
            for raw_row in reader:
                yield self._normalizer.normalize_row(raw_row, config)
