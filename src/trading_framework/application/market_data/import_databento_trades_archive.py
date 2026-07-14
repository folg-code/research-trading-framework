"""Import a Databento DBN trades archive into a WORKING dataset version."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from trading_framework import __version__ as framework_version
from trading_framework.infrastructure.importers.databento import (
    DatabentoDBNInspector,
    DatabentoDBNTradeReader,
)
from trading_framework.infrastructure.storage.import_manifest_store import write_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.infrastructure.validation.trade_validator import TradeBatchValidator
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.importers import (
    MANIFEST_VERSION,
    ArchiveInspectionResult,
    DatabentoTradesArchiveImportConfig,
    ImportManifest,
)
from trading_framework.market.models import MarketTrade
from trading_framework.market.repositories import TradeDatasetRepository
from trading_framework.market.validation import TradeValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


class TradesArchiveReader(Protocol):
    """Decode trades from a vendor archive."""

    def iter_trades(
        self,
        path: Path,
        *,
        provider_symbol: str | None = None,
    ) -> Iterator[MarketTrade]: ...


class TradesArchiveInspector(Protocol):
    """Inspect a vendor trades archive."""

    def inspect_with_checksum(self, path: Path) -> tuple[ArchiveInspectionResult, str]: ...


@dataclass(frozen=True, slots=True)
class ImportDatabentoTradesArchiveResult:
    """Outcome of a Databento trades archive import."""

    dataset_ref: DatasetRef
    validation_result: ValidationResult
    manifest: ImportManifest


def _dataset_time_range(
    trades: list[MarketTrade],
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    if not trades:
        return fallback, fallback
    ordered = sorted(trades, key=lambda trade: trade.event_at)
    return ordered[0].event_at, ordered[-1].event_at


def _build_lineage(
    config: DatabentoTradesArchiveImportConfig,
    inspection: ArchiveInspectionResult,
) -> Mapping[str, str]:
    lineage = {
        "source_path": str(config.path),
        "provider_symbol": config.symbol_mapping.provider_symbol,
        "instrument_id": config.symbol_mapping.instrument_id.value,
    }
    if inspection.dataset is not None:
        lineage["databento_dataset"] = inspection.dataset
    if config.lineage is not None:
        lineage = {**config.lineage, **lineage}
    return lineage


def import_databento_trades_archive(
    config: DatabentoTradesArchiveImportConfig,
    *,
    storage_root: Path,
    inspector: TradesArchiveInspector | None = None,
    reader: TradesArchiveReader | None = None,
    validator: TradeValidator | None = None,
    repository: TradeDatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
) -> ImportDatabentoTradesArchiveResult:
    """Inspect, decode, validate and register a WORKING trades dataset version."""
    archive_inspector = inspector or DatabentoDBNInspector()
    archive_reader = reader or DatabentoDBNTradeReader()
    trade_validator = validator or TradeBatchValidator()
    trade_repository = repository or ParquetTradeDatasetRepository(storage_root)
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()

    inspection, source_checksum = archive_inspector.inspect_with_checksum(config.path)
    provider_symbol = config.symbol_mapping.provider_symbol
    trades = list(
        archive_reader.iter_trades(config.path, provider_symbol=provider_symbol),
    )
    validation_result = trade_validator.validate(trades)
    validation_status = (
        ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
    )

    imported_at = utc_clock.now()
    dataset_ref = dataset_registry.allocate_ref(config.dataset_id)
    decode_row_count = len(trades)
    rejected_row_count = 0
    manifest = ImportManifest(
        manifest_version=MANIFEST_VERSION,
        source_path=str(config.path),
        source_format=inspection.source_format,
        source_checksum_sha256=source_checksum,
        vendor_schema=inspection.vendor_schema,
        symbol_mapping={
            config.symbol_mapping.provider_symbol: config.symbol_mapping.instrument_id.value,
        },
        decode_row_count=decode_row_count,
        rejected_row_count=rejected_row_count,
        imported_at_utc=imported_at,
        normalization_version=config.normalization_version,
        framework_version=framework_version,
    )
    write_import_manifest(storage_root, dataset_ref, manifest)

    if validation_result.is_valid:
        trade_repository.write_trades(dataset_ref, trades)

    start_at, end_at = _dataset_time_range(trades, fallback=imported_at)
    metadata = DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=config.dataset_id.instrument_id,
        timeframe=config.dataset_id.timeframe,
        provider=config.dataset_id.provider,
        source_id=config.dataset_id.source_id,
        data_type=config.dataset_id.data_type,
        start_at=start_at,
        end_at=end_at,
        schema_version=config.schema_version,
        normalization_version=config.normalization_version,
        validation_status=validation_status,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=decode_row_count if validation_result.is_valid else 0,
        checksum=source_checksum,
        created_at=imported_at,
        lineage=_build_lineage(config, inspection),
    )
    dataset_registry.register(metadata)

    return ImportDatabentoTradesArchiveResult(
        dataset_ref=dataset_ref,
        validation_result=validation_result,
        manifest=manifest,
    )
