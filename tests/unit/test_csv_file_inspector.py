"""CSV file inspector tests."""

from pathlib import Path

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.importers.csv import CsvFileInspector
from trading_framework.market.importers import DetectedFileFormat, FileInspector

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "csv"


def test_csv_file_inspector_detects_columns_and_timestamp_candidates() -> None:
    inspector = CsvFileInspector()
    result = inspector.inspect(_FIXTURES_DIR / "sample_ohlcv.csv")

    assert result.format is DetectedFileFormat.CSV
    assert result.columns == ("timestamp", "open", "high", "low", "close", "volume")
    assert result.timestamp_column_candidates == ("timestamp",)
    assert result.row_estimate == 2
    assert result.encoding in {"utf-8", "utf-8-sig"}


def test_csv_file_inspector_rejects_missing_file() -> None:
    inspector = CsvFileInspector()
    with pytest.raises(ValidationError, match="does not exist"):
        inspector.inspect(_FIXTURES_DIR / "missing.csv")


def test_csv_file_inspector_rejects_empty_header(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("\n", encoding="utf-8")

    inspector = CsvFileInspector()
    with pytest.raises(ValidationError, match="no columns"):
        inspector.inspect(path)


def test_csv_file_inspector_satisfies_protocol() -> None:
    inspector: FileInspector = CsvFileInspector()
    result = inspector.inspect(_FIXTURES_DIR / "sample_ohlcv.csv")
    assert result.row_estimate == 2
