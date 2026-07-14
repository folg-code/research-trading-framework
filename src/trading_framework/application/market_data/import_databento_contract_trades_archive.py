"""Import outright contracts from a Databento DBN trades archive."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from trading_framework import __version__ as framework_version
from trading_framework.infrastructure.importers.databento import DatabentoDBNInspector
from trading_framework.infrastructure.importers.databento.contract_reader import (
    StorageTradeFields,
)
from trading_framework.infrastructure.storage.import_manifest_store import write_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.validation.trade_validator import TradeBatchValidator
from trading_framework.market.contracts import (
    contract_instrument_id,
    trade_session_dates_from_ns,
    validate_contract_code,
    validate_product_code,
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
from trading_framework.market.validation import ValidationResult
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
    ordered = sorted(records, key=lambda record: record.ts_event_ns)
    return ordered[0].event_at(), ordered[-1].event_at()


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
    storage_trades: list[StorageTradeFields],
    *,
    product: str,
    contract_code: str,
    source_file: str,
    resolver: CmeEsRthSessionResolver,
) -> list[ContractTradeRecord]:
    validated_product = validate_product_code(product)
    validated_contract_code = validate_contract_code(contract_code)
    session_dates = trade_session_dates_from_ns(
        [trade["ts_event_ns"] for trade in storage_trades],
        resolver=resolver,
    )
    return [
        ContractTradeRecord.from_prevalidated_identity(
            validated_product=validated_product,
            validated_contract_code=validated_contract_code,
            ts_event_ns=trade["ts_event_ns"],
            ts_recv_ns=trade["ts_recv_ns"],
            price_nanos=trade["price_nanos"],
            size=trade["size"],
            instrument_id=trade["instrument_id"],
            sequence=trade["sequence"],
            publisher_id=trade["publisher_id"],
            side=trade["side"],
            session_date=session_date,
            source_file=source_file,
        )
        for trade, session_date in zip(storage_trades, session_dates, strict=True)
    ]


def import_databento_contract_trades_archive(
    config: DatabentoContractTradesArchiveImportConfig,
    *,
    storage_root: Path,
    inspector: TradesArchiveInspector | None = None,
    reader: ContractTradesArchiveReader | None = None,
    trade_validator: TradeBatchValidator | None = None,
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
    trade_validator = trade_validator or TradeBatchValidator()
    contract_repository = repository or ParquetContractTradeDatasetRepository(storage_root)
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()
    resolver = session_resolver or CmeEsRthSessionResolver()

    inspection, source_checksum = archive_inspector.inspect_with_checksum(config.path)
    if isinstance(archive_reader, DatabentoDBNContractTradeReader):
        storage_by_contract, rejected_spread_rows = archive_reader.decode_contract_storage_trades(
            config.path,
            product=config.product,
        )
    else:
        trades_by_contract, rejected_spread_rows = archive_reader.decode_contract_trades(
            config.path,
            product=config.product,
        )
        from trading_framework.market.contracts.storage_codec import (
            MISSING_TS_RECV_NS,
            price_nanos_from_decimal,
            utc_ns_from_datetime,
        )

        storage_by_contract = {
            contract_code: [
                StorageTradeFields(
                    ts_event_ns=utc_ns_from_datetime(trade.event_at),
                    ts_recv_ns=(
                        MISSING_TS_RECV_NS
                        if trade.received_at is None
                        else utc_ns_from_datetime(trade.received_at)
                    ),
                    price_nanos=price_nanos_from_decimal(trade.price.value),
                    size=trade.size.value,
                    instrument_id=0,
                    sequence=trade.sequence or 0,
                    publisher_id=0,
                    side=trade.side.value,
                )
                for trade in trades
            ]
            for contract_code, trades in trades_by_contract.items()
        }

    imported_at = utc_clock.now()
    contract_results: list[ContractTradesImportResult] = []
    for contract_code in sorted(storage_by_contract):
        storage_trades = storage_by_contract[contract_code]
        records = _records_for_contract(
            storage_trades,
            product=config.product,
            contract_code=contract_code,
            source_file=config.path.name,
            resolver=resolver,
        )
        validation_result = trade_validator.validate_records(records)
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
