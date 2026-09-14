"""Unit tests for list_published_datasets (Sprint 064 T004)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trading_framework.application.market_data.list_published_datasets import (
    list_published_datasets,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import dataset_metadata_path
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.time.models.timeframe import Timeframe

_START_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
_END_AT = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)


def _dataset_ref(instrument: str, version: int = 1) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(instrument),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
        ),
        version=version,
    )


def _metadata(dataset_ref: DatasetRef, *, lifecycle: DatasetLifecycleState) -> DatasetMetadata:
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=dataset_ref.dataset_id.instrument_id,
        timeframe=dataset_ref.dataset_id.timeframe,
        provider=dataset_ref.dataset_id.provider,
        source_id=dataset_ref.dataset_id.source_id,
        data_type=dataset_ref.dataset_id.data_type,
        start_at=_START_AT,
        end_at=_END_AT,
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=lifecycle,
        row_count=42,
        checksum="abc123",
        created_at=_START_AT,
    )


def test_list_published_datasets_returns_only_published(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)

    published_ref = _dataset_ref("ES.c.0")
    registry.register(_metadata(published_ref, lifecycle=DatasetLifecycleState.WORKING))
    registry.update(_metadata(published_ref, lifecycle=DatasetLifecycleState.PUBLISHED))

    working_ref = _dataset_ref("NQ.c.0")
    registry.register(_metadata(working_ref, lifecycle=DatasetLifecycleState.WORKING))

    summaries = list_published_datasets(storage_root)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.dataset_ref == str(published_ref)
    assert summary.instrument_id == "ES.c.0"
    assert summary.timeframe == "1m"
    assert summary.start_at == _START_AT
    assert summary.end_at == _END_AT
    assert summary.row_count == 42


def test_list_published_datasets_on_missing_storage_root_is_empty(tmp_path: Path) -> None:
    assert list_published_datasets(tmp_path / "does-not-exist") == ()


def test_list_published_datasets_skips_corrupt_metadata_file(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)

    published_ref = _dataset_ref("ES.c.0")
    registry.register(_metadata(published_ref, lifecycle=DatasetLifecycleState.WORKING))
    registry.update(_metadata(published_ref, lifecycle=DatasetLifecycleState.PUBLISHED))

    corrupt_ref = _dataset_ref("NQ.c.0")
    registry.register(_metadata(corrupt_ref, lifecycle=DatasetLifecycleState.WORKING))
    metadata_path = dataset_metadata_path(storage_root, corrupt_ref)
    metadata_path.write_text("{not valid json", encoding="utf-8")

    summaries = list_published_datasets(storage_root)

    assert [summary.instrument_id for summary in summaries] == ["ES.c.0"]


def test_list_published_datasets_sorted_by_metadata_path(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)

    for instrument in ("NQ.c.0", "ES.c.0"):
        ref = _dataset_ref(instrument)
        registry.register(_metadata(ref, lifecycle=DatasetLifecycleState.WORKING))
        registry.update(_metadata(ref, lifecycle=DatasetLifecycleState.PUBLISHED))

    summaries = list_published_datasets(storage_root)

    assert [summary.instrument_id for summary in summaries] == sorted(
        summary.instrument_id for summary in summaries
    )
