"""Import Databento contract trades archive workflow tests."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.application.market_data.import_databento_contract_trades_archive import (
    import_databento_contract_trades_archive,
)
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.import_manifest_store import read_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.market.contracts import MARKET_TRADE_CONTRACT_SCHEMA_VERSION
from trading_framework.market.datasets import DatasetLifecycleState, ValidationStatus
from trading_framework.market.importers import (
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    DatabentoContractTradesArchiveImportConfig,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.repositories import HistoricalTradeQuery
from trading_framework.time.clocks.fixed import FixedClock

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_SOURCE_CHECKSUM = "deadbeef" * 8


class _FakeInspector:
    def inspect_with_checksum(self, path: Path) -> tuple[ArchiveInspectionResult, str]:
        return (
            ArchiveInspectionResult(
                path=path,
                source_format=ArchiveSourceFormat.DATABENTO_DBN,
                vendor_schema="trades",
                nbytes=128,
                dataset="GLBX.MDP3",
                symbols=("NQ.FUT",),
                start_at=_IMPORTED_AT,
                end_at=_IMPORTED_AT,
            ),
            _SOURCE_CHECKSUM,
        )


def _trade(second: int) -> MarketTrade:
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC),
        side=TradeSide.BUY,
    )


class _FakeReader:
    def decode_contract_trades(
        self,
        path: Path,
        *,
        product: str,
    ) -> tuple[dict[str, list[MarketTrade]], int]:
        return {
            "NQU5": [_trade(0), _trade(1)],
            "NQZ5": [_trade(2)],
        }, 3


def _import_config(path: Path) -> DatabentoContractTradesArchiveImportConfig:
    return DatabentoContractTradesArchiveImportConfig(
        path=path,
        product="NQ",
        source_id="nq-cme-trades-20250713",
        schema_version=MARKET_TRADE_CONTRACT_SCHEMA_VERSION,
        normalization_version="databento-contract-trades-v1",
        lineage={"source_file": path.name},
    )


def test_import_databento_contract_trades_archive_splits_contracts(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetContractTradeDatasetRepository(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")

    result = import_databento_contract_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        inspector=_FakeInspector(),
        reader=_FakeReader(),
        registry=registry,
        repository=repository,
        clock=FixedClock(_IMPORTED_AT),
    )

    assert result.rejected_spread_row_count == 3
    assert len(result.contracts) == 2
    assert {contract.contract_code for contract in result.contracts} == {"NQU5", "NQZ5"}

    nqu5 = next(contract for contract in result.contracts if contract.contract_code == "NQU5")
    metadata = registry.get(nqu5.dataset_ref)
    manifest = read_import_manifest(storage_root, nqu5.dataset_ref)

    assert metadata.instrument_id.value == "NQ.NQU5"
    assert metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert metadata.validation_status is ValidationStatus.PASSED
    assert metadata.schema_version == MARKET_TRADE_CONTRACT_SCHEMA_VERSION
    assert metadata.row_count == 2
    assert manifest.decode_row_count == 2
    assert manifest.symbol_mapping == {"NQU5": "NQ.NQU5"}

    stored = repository.query_records(
        HistoricalTradeQuery(
            dataset_ref=nqu5.dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        )
    )
    assert len(stored) == 2
    assert stored[0].actual_contract == "NQU5"
    assert stored[0].source_file == "sample.dbn.zst"
