"""File inspection contract tests."""

from pathlib import Path

from trading_framework.market.importers import (
    DetectedFileFormat,
    FileInspectionResult,
    FileInspector,
)


class _StubFileInspector:
    def inspect(self, path: Path) -> FileInspectionResult:
        return FileInspectionResult(
            path=path,
            format=DetectedFileFormat.CSV,
            columns=("timestamp", "open", "high", "low", "close", "volume"),
            row_estimate=100,
            timestamp_column_candidates=("timestamp",),
            encoding="utf-8",
        )


def test_file_inspection_result_stores_metadata() -> None:
    result = FileInspectionResult(
        path=Path("sample.csv"),
        format=DetectedFileFormat.CSV,
        columns=("timestamp", "open"),
        row_estimate=None,
        timestamp_column_candidates=("timestamp",),
    )
    assert result.format is DetectedFileFormat.CSV
    assert result.columns == ("timestamp", "open")


def test_file_inspector_protocol_is_implementable() -> None:
    inspector: FileInspector = _StubFileInspector()
    result = inspector.inspect(Path("sample.csv"))
    assert result.row_estimate == 100
