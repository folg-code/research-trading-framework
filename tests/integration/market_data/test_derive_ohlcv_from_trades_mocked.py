"""Tier 1 integration test for derived OHLCV with synthetic mocked trades."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from tests.fixtures.databento import build_mock_dbn_store
from tests.fixtures.market import synthetic_trade_row_specs_across_minutes
from trading_framework.application.market_data import (
    QueryHistoricalRequest,
    derive_ohlcv_from_trades,
    finalize_dataset,
    import_databento_trades_archive,
    publish_dataset,
    query_historical,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    DerivedOhlcvFromTradesConfig,
)
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)
_DERIVED_AT = datetime(2025, 7, 14, 9, 0, tzinfo=UTC)
_DERIVED_PUBLISHED_AT = datetime(2025, 7, 14, 10, 0, tzinfo=UTC)


def _import_config(path: Path) -> DatabentoTradesArchiveImportConfig:
    return DatabentoTradesArchiveImportConfig(
        path=path,
        dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="mocked-trades-derive",
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-trade-v1",
        normalization_version="databento-trades-v1",
    )


def test_mocked_trades_derive_finalize_publish_query_flow(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"mocked-dbn-archive")
    mock_store = build_mock_dbn_store(specs=synthetic_trade_row_specs_across_minutes())

    with (
        patch(
            "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
            return_value=mock_store,
        ),
        patch(
            "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
            return_value=mock_store,
        ),
    ):
        import_result = import_databento_trades_archive(
            _import_config(archive_path),
            storage_root=storage_root,
            registry=registry,
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

    derive_result = derive_ohlcv_from_trades(
        DerivedOhlcvFromTradesConfig(
            source_dataset_ref=import_result.dataset_ref,
            target_dataset_id=DatasetId(
                instrument_id=Identifier("nq"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider=DERIVED_OHLCV_PROVIDER,
                source_id="mocked-derived-1m",
            ),
            schema_version="market-bar-v1",
        ),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
    )

    assert derive_result.validation_result.is_valid is True
    assert derive_result.bar_count == 2

    finalize_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_PUBLISHED_AT),
    )
    published_metadata = registry.get(derive_result.dataset_ref)
    assert published_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert published_metadata.validation_status is ValidationStatus.PASSED

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
    assert bars[0].open.value == Decimal("100.0")
    assert bars[1].close.value == Decimal("101.0")
