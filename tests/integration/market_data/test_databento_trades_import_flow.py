"""Integration tests for the Databento trades import vertical slice."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.application.market_data import (
    QueryTradesRequest,
    finalize_dataset,
    import_databento_trades_archive,
    publish_dataset,
    query_trades,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.import_manifest_store import read_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.importers import (
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    DatabentoTradesArchiveImportConfig,
    SymbolMapping,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)
_SOURCE_CHECKSUM = "abc12345" * 8


class _FakeInspector:
    def inspect_with_checksum(self, path: Path) -> tuple[ArchiveInspectionResult, str]:
        return (
            ArchiveInspectionResult(
                path=path,
                source_format=ArchiveSourceFormat.DATABENTO_DBN,
                vendor_schema="trades",
                nbytes=64,
                dataset="GLBX.MDP3",
                symbols=("NQ.FUT",),
                start_at=_IMPORTED_AT,
                end_at=datetime(2025, 7, 13, 22, 0, 2, tzinfo=UTC),
            ),
            _SOURCE_CHECKSUM,
        )


class _FakeReader:
    def __init__(self, trades: list[MarketTrade]) -> None:
        self._trades = trades

    def iter_trades(
        self, path: Path, *, provider_symbol: str | None = None
    ) -> Iterator[MarketTrade]:
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
            source_id="integration-trades",
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-trade-v1",
        normalization_version="databento-trades-v1",
        lineage={"source_file": path.name},
    )


def test_databento_trades_import_finalize_publish_query_flow(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")
    trades = [_trade(0), _trade(1), _trade(2)]

    import_result = import_databento_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        registry=registry,
        inspector=_FakeInspector(),
        reader=_FakeReader(trades),
        clock=FixedClock(_IMPORTED_AT),
    )
    working_metadata = registry.get(import_result.dataset_ref)
    manifest = read_import_manifest(storage_root, import_result.dataset_ref)

    assert import_result.validation_result.is_valid is True
    assert working_metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert working_metadata.validation_status is ValidationStatus.PASSED
    assert working_metadata.row_count == 3
    assert working_metadata.checksum == _SOURCE_CHECKSUM
    assert manifest.decode_row_count == 3

    finalize_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    finalized_metadata = registry.get(import_result.dataset_ref)
    assert finalized_metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert finalized_metadata.checksum == _SOURCE_CHECKSUM

    publish_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )
    published_metadata = registry.get(import_result.dataset_ref)
    assert published_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert published_metadata.published_at == _PUBLISHED_AT

    queried = query_trades(
        QueryTradesRequest(
            dataset_ref=import_result.dataset_ref,
            start_at=published_metadata.start_at,
            end_at=published_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )

    assert len(queried) == 3
    assert [trade.event_at.second for trade in queried] == [0, 1, 2]
    assert all(trade.event_at.tzinfo is not None for trade in queried)
