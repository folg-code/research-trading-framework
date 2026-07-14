"""Import Databento trades archive workflow tests."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.application.market_data.import_databento_trades_archive import (
    import_databento_trades_archive,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.import_manifest_store import read_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.importers import (
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    DatabentoTradesArchiveImportConfig,
    SymbolMapping,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.repositories import HistoricalTradeQuery
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

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


class _FakeReader:
    def __init__(self, trades: list[MarketTrade]) -> None:
        self._trades = trades
        self.last_provider_symbol: str | None = None

    def iter_trades(
        self, path: Path, *, provider_symbol: str | None = None
    ) -> Iterator[MarketTrade]:
        self.last_provider_symbol = provider_symbol
        yield from self._trades


def _trade(second: int) -> MarketTrade:
    return MarketTrade(
        price=Price(Decimal("22860.75")),
        size=Volume(119),
        event_at=datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC),
        side=TradeSide.BUY,
    )


def _import_config(path: Path) -> DatabentoTradesArchiveImportConfig:
    return DatabentoTradesArchiveImportConfig(
        path=path,
        dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq_cme_trades_2025",
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-trade-v1",
        normalization_version="databento-trades-v1",
        lineage={"source_file": path.name},
    )


def test_import_databento_trades_archive_registers_working_dataset(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetTradeDatasetRepository(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")
    trades = [_trade(0), _trade(1)]
    reader = _FakeReader(trades)

    result = import_databento_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        inspector=_FakeInspector(),
        reader=reader,
        registry=registry,
        repository=repository,
        clock=FixedClock(_IMPORTED_AT),
    )

    metadata = registry.get(result.dataset_ref)
    manifest = read_import_manifest(storage_root, result.dataset_ref)

    assert reader.last_provider_symbol == "NQ.FUT"
    assert result.validation_result.is_valid is True
    assert metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert metadata.validation_status is ValidationStatus.PASSED
    assert metadata.checksum == _SOURCE_CHECKSUM
    assert metadata.row_count == 2
    assert manifest.decode_row_count == 2
    assert manifest.source_checksum_sha256 == _SOURCE_CHECKSUM

    stored = repository.query_trades(
        HistoricalTradeQuery(
            dataset_ref=result.dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        )
    )
    assert len(stored) == 2
