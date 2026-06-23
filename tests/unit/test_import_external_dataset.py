"""Import external dataset use case tests."""

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.application.market_data import (
    ImportExternalDatasetRequest,
    import_external_dataset,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, ValidationStatus
from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
from trading_framework.market.repositories import HistoricalBarQuery
from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.market.validation import ValidationSeverity
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "csv"
_FIXED_NOW = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


def _request(path: Path) -> ImportExternalDatasetRequest:
    return ImportExternalDatasetRequest(
        path=path,
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
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
        lineage={"source_file": str(path.name)},
    )


def test_import_external_dataset_registers_working_version(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)
    result = import_external_dataset(
        _request(_FIXTURES_DIR / "sample_ohlcv.csv"),
        storage_root=storage_root,
        registry=registry,
        repository=repository,
        clock=FixedClock(_FIXED_NOW),
    )

    assert result.validation_result.is_valid is True
    metadata = registry.get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert metadata.validation_status is ValidationStatus.PASSED
    assert metadata.row_count == 2

    bars = repository.query_bars(
        HistoricalBarQuery(
            dataset_ref=result.dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        )
    )
    assert len(bars) == 2


def test_import_external_dataset_marks_failed_validation_without_writing_bars(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")

    result = import_external_dataset(
        _request(empty_csv),
        storage_root=storage_root,
        registry=registry,
        repository=repository,
        clock=FixedClock(_FIXED_NOW),
    )

    assert result.validation_result.is_valid is False
    assert result.validation_result.issues[0].severity is ValidationSeverity.ERROR
    metadata = registry.get(result.dataset_ref)
    assert metadata.validation_status is ValidationStatus.FAILED
    assert (
        repository.query_bars(
            HistoricalBarQuery(
                dataset_ref=result.dataset_ref,
                start_at=metadata.start_at,
                end_at=metadata.end_at,
            )
        )
        == []
    )
