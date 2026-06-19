"""Dataset metadata tests."""

from datetime import UTC, datetime

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.time.models.timeframe import Timeframe


def _sample_metadata() -> DatasetMetadata:
    dataset_ref = DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
        ),
        version=1,
    )
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 1, 0, tzinfo=UTC)
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=Identifier("ES.c.0"),
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
        data_type="ohlcv",
        start_at=start_at,
        end_at=end_at,
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=60,
        checksum="abc123",
        created_at=start_at,
        lineage={"source_file": "sample.csv"},
    )


def test_dataset_metadata_round_trip_dict() -> None:
    metadata = _sample_metadata()
    restored = DatasetMetadata.from_dict(metadata.to_dict())
    assert restored == metadata


def test_dataset_metadata_serializes_enums_and_datetimes() -> None:
    payload = _sample_metadata().to_dict()
    assert payload["validation_status"] == "passed"
    assert payload["lifecycle_status"] == "working"
    assert payload["start_at"].endswith("+00:00")
