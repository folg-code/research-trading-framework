"""Import an external OHLCV dataset into a WORKING dataset version."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.importers.csv.ohlcv import CsvOhlcvImporter
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.validation.ohlcv_validator import OhlcvBarValidator
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketBar
from trading_framework.market.normalization import NormalizedBarRow, OhlcvImportConfig
from trading_framework.market.repositories import DatasetRepository
from trading_framework.market.validation import OhlcvValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


@dataclass(frozen=True, slots=True)
class ImportExternalDatasetRequest:
    """Input for importing an external OHLCV file."""

    path: Path
    dataset_id: DatasetId
    import_config: OhlcvImportConfig
    schema_version: str
    normalization_version: str
    lineage: Mapping[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ImportExternalDatasetResult:
    """Outcome of an external dataset import."""

    dataset_ref: DatasetRef
    validation_result: ValidationResult


def _market_bar_from_row(row: NormalizedBarRow) -> MarketBar:
    return MarketBar(
        open=Price(row.open),
        high=Price(row.high),
        low=Price(row.low),
        close=Price(row.close),
        volume=Volume(row.volume),
        observed_at=row.observed_at,
        available_at=row.available_at,
    )


def _dataset_time_range(
    bars: list[MarketBar],
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    if not bars:
        return fallback, fallback
    return bars[0].observed_at, bars[-1].observed_at


def import_external_dataset(
    request: ImportExternalDatasetRequest,
    *,
    storage_root: Path,
    importer: CsvOhlcvImporter | None = None,
    validator: OhlcvValidator | None = None,
    repository: DatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
) -> ImportExternalDatasetResult:
    """Inspect, normalize, validate and register a WORKING dataset version."""
    csv_importer = importer or CsvOhlcvImporter()
    bar_validator = validator or OhlcvBarValidator()
    bar_repository = repository or ParquetDatasetRepository(storage_root)
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()

    normalized_rows = list(csv_importer.iter_rows(request.path, request.import_config))
    bars = [_market_bar_from_row(row) for row in normalized_rows]
    validation_result = bar_validator.validate(bars)
    validation_status = (
        ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
    )

    created_at = utc_clock.now()
    start_at, end_at = _dataset_time_range(bars, fallback=created_at)
    dataset_ref = dataset_registry.allocate_ref(request.dataset_id)

    if validation_result.is_valid:
        bar_repository.write_bars(dataset_ref, bars)

    metadata = DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=request.dataset_id.instrument_id,
        timeframe=request.dataset_id.timeframe,
        provider=request.dataset_id.provider,
        source_id=request.dataset_id.source_id,
        data_type=request.dataset_id.data_type,
        start_at=start_at,
        end_at=end_at,
        schema_version=request.schema_version,
        normalization_version=request.normalization_version,
        validation_status=validation_status,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=len(bars),
        checksum="pending",
        created_at=created_at,
        lineage=request.lineage,
    )
    dataset_registry.register(metadata)

    return ImportExternalDatasetResult(
        dataset_ref=dataset_ref,
        validation_result=validation_result,
    )
