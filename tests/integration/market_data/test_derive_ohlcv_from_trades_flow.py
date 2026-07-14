"""Integration tests for derived OHLCV from trades vertical slice."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.application.market_data import (
    QueryHistoricalRequest,
    derive_ohlcv_from_trades,
    finalize_dataset,
    import_databento_trades_archive,
    publish_dataset,
    query_historical,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
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
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_TRADES_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)
_DERIVED_AT = datetime(2025, 7, 14, 9, 0, tzinfo=UTC)
_DERIVED_PUBLISHED_AT = datetime(2025, 7, 14, 10, 0, tzinfo=UTC)
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


def _derive_config(source_ref: DatasetRef) -> DerivedOhlcvFromTradesConfig:
    return DerivedOhlcvFromTradesConfig(
        source_dataset_ref=source_ref,
        target_dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id="integration-derived-1m",
        ),
        schema_version="market-bar-v1",
    )


def test_derived_ohlcv_from_trades_finalize_publish_query_flow(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake")

    trades_import = import_databento_trades_archive(
        _import_config(archive_path),
        storage_root=storage_root,
        registry=registry,
        inspector=_FakeInspector(),
        reader=_FakeReader(_synthetic_trades_across_minutes()),
        clock=FixedClock(_IMPORTED_AT),
    )
    finalize_dataset(
        trades_import.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        trades_import.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_TRADES_PUBLISHED_AT),
    )
    trades_metadata = registry.get(trades_import.dataset_ref)
    assert trades_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED

    derive_result = derive_ohlcv_from_trades(
        _derive_config(trades_import.dataset_ref),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
    )
    working_metadata = registry.get(derive_result.dataset_ref)
    lineage = working_metadata.lineage or {}

    assert derive_result.validation_result.is_valid is True
    assert derive_result.bar_count == 2
    assert working_metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert working_metadata.validation_status is ValidationStatus.PASSED
    assert working_metadata.provider == DERIVED_OHLCV_PROVIDER
    assert working_metadata.checksum == "pending"
    assert lineage["source_dataset_ref"] == str(trades_import.dataset_ref)
    assert lineage["derivation_method"] == TRADES_TO_BARS_DERIVATION_METHOD
    assert lineage["derivation_version"] == TRADES_TO_BARS_VERSION

    finalize_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    finalized_metadata = registry.get(derive_result.dataset_ref)
    assert finalized_metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert finalized_metadata.checksum != "pending"
    assert finalized_metadata.row_count == 2

    publish_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_PUBLISHED_AT),
    )
    published_metadata = registry.get(derive_result.dataset_ref)
    assert published_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert published_metadata.published_at == _DERIVED_PUBLISHED_AT

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=derive_result.dataset_ref,
            start_at=published_metadata.start_at,
            end_at=published_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )

    assert len(bars) == 2
    assert bars[0].open.value == Decimal("100.00")
    assert bars[0].close.value == Decimal("100.75")
    assert bars[1].close.value == Decimal("101.00")
    assert bars[0].observed_at < bars[1].observed_at
    assert all(bar.observed_at.tzinfo is not None for bar in bars)
