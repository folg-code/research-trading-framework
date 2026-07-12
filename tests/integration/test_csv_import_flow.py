"""Integration tests for the market data CSV import vertical slice."""

from datetime import UTC, datetime
from pathlib import Path

from tests.fixtures.market_data import OHLCV_SAMPLE_1M_ROW_COUNT
from trading_framework.application.market_data import (
    ImportExternalDatasetRequest,
    QueryHistoricalRequest,
    finalize_dataset,
    import_external_dataset,
    publish_dataset,
    query_historical,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_PUBLISHED_AT = datetime(2024, 6, 2, 8, 0, tzinfo=UTC)
_IMPORTED_AT = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


def _import_request(path: Path) -> ImportExternalDatasetRequest:
    return ImportExternalDatasetRequest(
        path=path,
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="integration-sample",
        ),
        import_config=OhlcvImportConfig(
            column_mapping=OhlcvColumnMapping(
                timestamp="timestamp",
                open="open",
                high="high",
                low="low",
                close="close",
                volume="volume",
            ),
            timeframe=Timeframe("1m"),
            timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
            source_timezone=UTC,
        ),
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        lineage={"source_file": path.name},
    )


def test_csv_import_finalize_publish_query_flow(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)

    import_result = import_external_dataset(
        _import_request(ohlcv_sample_1m_path),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_IMPORTED_AT),
    )
    working_metadata = registry.get(import_result.dataset_ref)

    assert import_result.validation_result.is_valid is True
    assert working_metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert working_metadata.validation_status is ValidationStatus.PASSED
    assert working_metadata.row_count == OHLCV_SAMPLE_1M_ROW_COUNT

    finalize_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    finalized_metadata = registry.get(import_result.dataset_ref)
    assert finalized_metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert finalized_metadata.checksum != "pending"

    publish_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )
    published_metadata = registry.get(import_result.dataset_ref)
    assert published_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert published_metadata.published_at == _PUBLISHED_AT

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=import_result.dataset_ref,
            start_at=published_metadata.start_at,
            end_at=published_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )

    assert len(bars) == OHLCV_SAMPLE_1M_ROW_COUNT
    assert bars[0].observed_at < bars[1].observed_at
    assert all(bar.observed_at.tzinfo is not None for bar in bars)
