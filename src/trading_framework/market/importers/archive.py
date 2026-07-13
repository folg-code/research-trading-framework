"""Archive import contracts for vendor DBN and similar sources."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class ArchiveSourceFormat(StrEnum):
    """Supported external archive container formats."""

    DATABENTO_DBN = "databento_dbn"


MANIFEST_VERSION = "1"


@dataclass(frozen=True, slots=True)
class ArchiveInspectionResult:
    """Summary of a vendor archive produced before import."""

    path: Path
    source_format: ArchiveSourceFormat
    vendor_schema: str
    nbytes: int
    dataset: str | None
    symbols: tuple[str, ...]
    start_at: datetime | None
    end_at: datetime | None
    row_estimate: int | None = None


@dataclass(frozen=True, slots=True)
class ImportManifest:
    """Persisted record of one archive import."""

    manifest_version: str
    source_path: str
    source_format: ArchiveSourceFormat
    source_checksum_sha256: str
    vendor_schema: str
    symbol_mapping: Mapping[str, str]
    decode_row_count: int
    rejected_row_count: int
    imported_at_utc: datetime
    normalization_version: str
    framework_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manifest to a JSON-compatible dictionary."""
        return {
            "manifest_version": self.manifest_version,
            "source_path": self.source_path,
            "source_format": self.source_format.value,
            "source_checksum_sha256": self.source_checksum_sha256,
            "vendor_schema": self.vendor_schema,
            "symbol_mapping": dict(self.symbol_mapping),
            "decode_row_count": self.decode_row_count,
            "rejected_row_count": self.rejected_row_count,
            "imported_at_utc": self.imported_at_utc.isoformat(),
            "normalization_version": self.normalization_version,
            "framework_version": self.framework_version,
        }


class ArchiveInspector(Protocol):
    """Inspect a vendor archive without performing a full import."""

    def inspect(self, path: Path) -> ArchiveInspectionResult:
        """Return structural metadata used to configure downstream import."""
