"""File inspection contracts for external market data imports."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class DetectedFileFormat(StrEnum):
    """Detected external file format."""

    CSV = "csv"
    PARQUET = "parquet"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class FileInspectionResult:
    """Summary of an external file produced before import."""

    path: Path
    format: DetectedFileFormat
    columns: tuple[str, ...]
    row_estimate: int | None
    timestamp_column_candidates: tuple[str, ...]
    encoding: str | None = None


class FileInspector(Protocol):
    """Inspect an external file without performing a full import."""

    def inspect(self, path: Path) -> FileInspectionResult:
        """Return structural metadata used to configure downstream import."""
