"""Tier 1 integration test for Databento trades import with mocked DBN decode."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from tests.fixtures.databento import SyntheticTradeRowSpec, build_mock_dbn_store
from trading_framework.application.market_data import (
    QueryTradesRequest,
    finalize_dataset,
    import_databento_trades_archive,
    publish_dataset,
    query_trades,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.import_manifest_store import read_import_manifest
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)


def _import_config(path: Path) -> DatabentoTradesArchiveImportConfig:
    return DatabentoTradesArchiveImportConfig(
        path=path,
        dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="mocked-trades",
        ),
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-trade-v1",
        normalization_version="databento-trades-v1",
    )


def test_mocked_dbn_import_finalize_publish_query_flow(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"mocked-dbn-archive")
    mock_store = build_mock_dbn_store(
        specs=[
            SyntheticTradeRowSpec(second=0, symbol="NQ.FUT"),
            SyntheticTradeRowSpec(second=1, symbol="NQ.FUT", side="A"),
        ]
    )

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

    working_metadata = registry.get(import_result.dataset_ref)
    manifest = read_import_manifest(storage_root, import_result.dataset_ref)

    assert import_result.validation_result.is_valid is True
    assert working_metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert working_metadata.validation_status is ValidationStatus.PASSED
    assert working_metadata.row_count == 2
    assert manifest.decode_row_count == 2

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

    trades = query_trades(
        QueryTradesRequest(
            dataset_ref=import_result.dataset_ref,
            start_at=working_metadata.start_at,
            end_at=working_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )

    assert len(trades) == 2
    assert trades[0].event_at <= trades[1].event_at
    assert all(trade.event_at.tzinfo is not None for trade in trades)
