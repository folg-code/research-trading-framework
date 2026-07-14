"""Import outright contracts from a Databento DBN trades archive."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from trading_framework import __version__ as framework_version
from trading_framework.infrastructure.importers.databento import (
    DatabentoDBNInspector,
)
from trading_framework.infrastructure.storage.import_manifest_store import write_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.validation.trade_validator import TradeBatchValidator
from trading_framework.market.contracts import (
    contract_instrument_id,
    trade_session_date,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.importers import (
    MANIFEST_VERSION,
    ArchiveInspectionResult,
    DatabentoContractTradesArchiveImportConfig,
    ImportManifest,
)
from trading_framework.market.models import MarketTrade
from trading_framework.market.validation import TradeValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


class ContractTradesArchiveReader(Protocol):
    """Decode outright contract trades from a vendor archive."""

    def decode_contract_trades(
        self,
        path: Path,
        *,
        product: str,
    ) -> tuple[dict[str, list[MarketTrade]], int]: ...


class TradesArchiveInspector(Protocol):
    """Inspect a vendor trades archive."""

    def inspect_with_checksum(self, path: Path) -> tuple[ArchiveInspectionResult, str]: ...


@dataclass(frozen=True, slots=True)
class ContractTradesImportResult:
    """Outcome for one imported outright contract dataset."""

    contract_code: str
    dataset_ref: DatasetRef
    validation_result: ValidationResult
    manifest: ImportManifest
    record_count: int


@dataclass(frozen=True, slots=True)
class ImportDatabentoContractTradesArchiveResult:
    """Outcome of a multi-contract Databento trades archive import."""

    contracts: tuple[ContractTradesImportResult, ...]
    rejected_spread_row_count: int
    source_checksum_sha256: str


def _dataset_time_range(
    records: list[ContractTradeRecord],
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    if not records:
        return fallback, fallback
    ordered = sorted(records, key=lambda record: record.trade.event_at)
    return ordered[0].trade.event_at, ordered[-1].trade.event_at


def _build_lineage(
    config: DatabentoContractTradesArchiveImportConfig,
    inspection: ArchiveInspectionResult,
    *,
    contract_code: str,
) -> Mapping[str, str]:
    lineage = {
        "source_path": str(config.path),
        "product": config.product,
        "actual_contract": contract_code,
        "instrument_id": contract_instrument_id(
            product=config.product,
            contract_code=contract_code,
        ).value,
    }
    if inspection.dataset is not None:
        lineage["databento_dataset"] = inspection.dataset
    if config.lineage is not None:
        lineage = {**config.lineage, **lineage}
    return lineage


def _records_for_contract(
    trades: list[MarketTrade],
    *,
    product: str,
    contract_code: str,
    source_file: str,
    resolver: CmeEsRthSessionResolver,
) -> list[ContractTradeRecord]:
    return [
        ContractTradeRecord(
            trade=trade,
            actual_contract=contract_code,
            product=product,
            session_date=trade_session_date(trade.event_at, resolver=resolver),
            source_file=source_file,
        )
        for trade in trades
    ]


def import_databento_contract_trades_archive(
    config: DatabentoContractTradesArchiveImportConfig,
    *,
    storage_root: Path,
    inspector: TradesArchiveInspector | None = None,
    reader: ContractTradesArchiveReader | None = None,
    validator: TradeValidator | None = None,
    repository: ParquetContractTradeDatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
    session_resolver: CmeEsRthSessionResolver | None = None,
) -> ImportDatabentoContractTradesArchiveResult:
    """Inspect, decode, split and register WORKING contract trade dataset versions."""
    from trading_framework.infrastructure.importers.databento.contract_reader import (
        DatabentoDBNContractTradeReader,
    )

    archive_inspector = inspector or DatabentoDBNInspector()
    archive_reader = reader or DatabentoDBNContractTradeReader()
    trade_validator = validator or TradeBatchValidator()
    contract_repository = repository or ParquetContractTradeDatasetRepository(storage_root)
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()
    resolver = session_resolver or CmeEsRthSessionResolver()

    inspection, source_checksum = archive_inspector.inspect_with_checksum(config.path)
    trades_by_contract, rejected_spread_rows = archive_reader.decode_contract_trades(
        config.path,
        product=config.product,
    )

    imported_at = utc_clock.now()
    contract_results: list[ContractTradesImportResult] = []
    for contract_code in sorted(trades_by_contract):
        trades = trades_by_contract[contract_code]
        records = _records_for_contract(
            trades,
            product=config.product,
            contract_code=contract_code,
            source_file=config.path.name,
            resolver=resolver,
        )
        validation_result = trade_validator.validate(trades)
        validation_status = (
            ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
        )
        dataset_ref = dataset_registry.allocate_ref(
            DatasetId(
                instrument_id=contract_instrument_id(
                    product=config.product,
                    contract_code=contract_code,
                ),
                data_type="trades",
                timeframe=Timeframe("tick"),
                provider="databento",
                source_id=config.source_id,
            )
        )
        manifest = ImportManifest(
            manifest_version=MANIFEST_VERSION,
            source_path=str(config.path),
            source_format=inspection.source_format,
            source_checksum_sha256=source_checksum,
            vendor_schema=inspection.vendor_schema,
            symbol_mapping={contract_code: dataset_ref.dataset_id.instrument_id.value},
            decode_row_count=len(records),
            rejected_row_count=0,
            imported_at_utc=imported_at,
            normalization_version=config.normalization_version,
            framework_version=framework_version,
        )
        write_import_manifest(storage_root, dataset_ref, manifest)

        if validation_result.is_valid:
            contract_repository.write_records(dataset_ref, records)

        start_at, end_at = _dataset_time_range(records, fallback=imported_at)
        metadata = DatasetMetadata(
            dataset_ref=dataset_ref,
            instrument_id=dataset_ref.dataset_id.instrument_id,
            timeframe=dataset_ref.dataset_id.timeframe,
            provider=dataset_ref.dataset_id.provider,
            source_id=dataset_ref.dataset_id.source_id,
            data_type=dataset_ref.dataset_id.data_type,
            start_at=start_at,
            end_at=end_at,
            schema_version=config.schema_version,
            normalization_version=config.normalization_version,
            validation_status=validation_status,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=len(records) if validation_result.is_valid else 0,
            checksum=source_checksum,
            created_at=imported_at,
            lineage=_build_lineage(config, inspection, contract_code=contract_code),
        )
        dataset_registry.register(metadata)
        contract_results.append(
            ContractTradesImportResult(
                contract_code=contract_code,
                dataset_ref=dataset_ref,
                validation_result=validation_result,
                manifest=manifest,
                record_count=len(records),
            )
        )

    return ImportDatabentoContractTradesArchiveResult(
        contracts=tuple(contract_results),
        rejected_spread_row_count=rejected_spread_rows,
        source_checksum_sha256=source_checksum,
    )
