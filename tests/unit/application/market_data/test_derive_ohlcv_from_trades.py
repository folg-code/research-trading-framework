"""Derive OHLCV from trades workflow tests."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data import finalize_dataset, publish_dataset
from trading_framework.application.market_data.derive_ohlcv_from_trades import (
    derive_ohlcv_from_trades,
)
from trading_framework.application.market_data.import_databento_trades_archive import (
    import_databento_trades_archive,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    TRADES_TO_BARS_DERIVATION_METHOD,
    TRADES_TO_BARS_VERSION,
    DerivedOhlcvFromTradesConfig,
)
from trading_framework.market.importers import (
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    DatabentoTradesArchiveImportConfig,
    SymbolMapping,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.repositories import HistoricalBarQuery
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_DERIVED_AT = datetime(2025, 7, 14, 9, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)
_SOURCE_CHECKSUM = "deadbeef" * 8


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
                end_at=datetime(2025, 7, 13, 22, 1, 0, tzinfo=UTC),
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


def _synthetic_trades_across_minutes() -> list[MarketTrade]:
    specs = [
        (datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC), "100.00", 10, 0),
        (datetime(2025, 7, 13, 22, 0, 15, tzinfo=UTC), "101.50", 5, 1),
        (datetime(2025, 7, 13, 22, 0, 45, tzinfo=UTC), "99.25", 8, 2),
        (datetime(2025, 7, 13, 22, 0, 59, 500_000, tzinfo=UTC), "100.75", 3, 3),
        (datetime(2025, 7, 13, 22, 1, 0, tzinfo=UTC), "101.00", 12, 4),
    ]
    return [
        MarketTrade(
            price=Price(Decimal(price)),
            size=Volume(size),
            event_at=event_at,
            side=TradeSide.BUY if sequence % 2 == 0 else TradeSide.SELL,
            sequence=sequence,
        )
        for event_at, price, size, sequence in specs
    ]


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
    )


def _derive_config(source_ref: DatasetRef) -> DerivedOhlcvFromTradesConfig:
    return DerivedOhlcvFromTradesConfig(
        source_dataset_ref=source_ref,
        target_dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id="nq_1m_from_trades_2025",
        ),
        schema_version="market-bar-v1",
    )


def _publish_trades_dataset(
    tmp_path: Path,
) -> tuple[Path, FileDatasetRegistry, DatasetRef]:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")

    import_result = import_databento_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        registry=registry,
        inspector=_FakeInspector(),
        reader=_FakeReader(_synthetic_trades_across_minutes()),
        clock=FixedClock(_IMPORTED_AT),
    )
    finalize_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )
    return storage_root, registry, import_result.dataset_ref


def test_derive_ohlcv_from_trades_registers_working_dataset_with_lineage(
    tmp_path: Path,
) -> None:
    storage_root, registry, source_ref = _publish_trades_dataset(tmp_path)
    bar_repository = ParquetDatasetRepository(storage_root)

    result = derive_ohlcv_from_trades(
        _derive_config(source_ref),
        storage_root=storage_root,
        registry=registry,
        bar_repository=bar_repository,
        clock=FixedClock(_DERIVED_AT),
    )

    metadata = registry.get(result.dataset_ref)
    lineage = metadata.lineage or {}

    assert result.validation_result.is_valid is True
    assert result.bar_count == 2
    assert result.source_dataset_ref == source_ref
    assert metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert metadata.validation_status is ValidationStatus.PASSED
    assert metadata.provider == DERIVED_OHLCV_PROVIDER
    assert metadata.data_type == "ohlcv"
    assert metadata.checksum == "pending"
    assert lineage["source_dataset_ref"] == str(source_ref)
    assert lineage["derivation_method"] == TRADES_TO_BARS_DERIVATION_METHOD
    assert lineage["derivation_version"] == TRADES_TO_BARS_VERSION
    assert lineage["target_timeframe"] == "1m"

    stored = bar_repository.query_bars(
        HistoricalBarQuery(
            dataset_ref=result.dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        )
    )
    assert len(stored) == 2
    assert stored[0].open.value == Decimal("100.00")
    assert stored[1].close.value == Decimal("101.00")


def test_derive_ohlcv_from_trades_rejects_unpublished_source(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")

    import_result = import_databento_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        registry=registry,
        inspector=_FakeInspector(),
        reader=_FakeReader(_synthetic_trades_across_minutes()),
        clock=FixedClock(_IMPORTED_AT),
    )

    with pytest.raises(Exception, match="source trades dataset must be published"):
        derive_ohlcv_from_trades(
            _derive_config(import_result.dataset_ref),
            storage_root=storage_root,
            registry=registry,
            clock=FixedClock(_DERIVED_AT),
        )
