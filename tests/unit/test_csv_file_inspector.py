"""CSV file inspector tests."""

from pathlib import Path

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.importers.csv import CsvFileInspector
from trading_framework.market.importers import DetectedFileFormat, FileInspector


def test_csv_file_inspector_detects_columns_and_timestamp_candidates(
    market_data_fixtures_dir: Path,
) -> None:
    inspector = CsvFileInspector()
    result = inspector.inspect(market_data_fixtures_dir / "sample_ohlcv.csv")

    assert result.format is DetectedFileFormat.CSV
    assert result.columns == ("timestamp", "open", "high", "low", "close", "volume")
    assert result.timestamp_column_candidates == ("timestamp",)
    assert result.row_estimate == 2
    assert result.encoding in {"utf-8", "utf-8-sig"}


def test_csv_file_inspector_rejects_missing_file(market_data_fixtures_dir: Path) -> None:
    inspector = CsvFileInspector()
    with pytest.raises(ValidationError, match="does not exist"):
        inspector.inspect(market_data_fixtures_dir / "missing.csv")


def test_csv_file_inspector_rejects_empty_header(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("\n", encoding="utf-8")

    inspector = CsvFileInspector()
    with pytest.raises(ValidationError, match="no columns"):
        inspector.inspect(path)


def test_csv_file_inspector_satisfies_protocol(market_data_fixtures_dir: Path) -> None:
    inspector: FileInspector = CsvFileInspector()
    result = inspector.inspect(market_data_fixtures_dir / "sample_ohlcv.csv")
    assert result.row_estimate == 2
