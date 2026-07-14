"""External file importer contracts."""

from trading_framework.market.importers.archive import (
    MANIFEST_VERSION,
    ArchiveInspectionResult,
    ArchiveInspector,
    ArchiveSourceFormat,
    ImportManifest,
)
from trading_framework.market.importers.checksum import compute_source_checksum_sha256
from trading_framework.market.importers.ohlcv_config import DatabentoOhlcvArchiveImportConfig
from trading_framework.market.importers.protocols import (
    DetectedFileFormat,
    FileInspectionResult,
    FileInspector,
)
from trading_framework.market.importers.trades_config import (
    DatabentoTradesArchiveImportConfig,
    SymbolMapping,
)

__all__ = [
    "MANIFEST_VERSION",
    "ArchiveInspectionResult",
    "ArchiveInspector",
    "ArchiveSourceFormat",
    "DatabentoOhlcvArchiveImportConfig",
    "DatabentoTradesArchiveImportConfig",
    "DetectedFileFormat",
    "FileInspectionResult",
    "FileInspector",
    "ImportManifest",
    "SymbolMapping",
    "compute_source_checksum_sha256",
]
