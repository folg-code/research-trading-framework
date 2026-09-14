"""Tests for infrastructure.storage.metadata.discovery (market-data layout
simplification: new vs. legacy layout, both must resolve via DatasetId.asset_class).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.discovery import (
    latest_dataset_ref,
    latest_published_dataset_ref,
    list_dataset_refs,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models.instrument import AssetClass
from trading_framework.time.models.timeframe import Timeframe

_START_AT = datetime(2024, 1, 1, tzinfo=UTC)
_END_AT = datetime(2024, 1, 2, tzinfo=UTC)


def _metadata(
    dataset_id: DatasetId, *, version: int, lifecycle: DatasetLifecycleState
) -> DatasetMetadata:
    dataset_ref = DatasetRef(dataset_id=dataset_id, version=version)
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=dataset_id.instrument_id,
        timeframe=dataset_id.timeframe,
        provider=dataset_id.provider,
        source_id=dataset_id.source_id,
        data_type=dataset_id.data_type,
        start_at=_START_AT,
        end_at=_END_AT,
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=lifecycle,
        row_count=1,
        checksum="abc123",
        created_at=_START_AT,
    )


def test_list_dataset_refs_new_layout(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_id = DatasetId(
        instrument_id=Identifier("BTCUSDT.P"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="binance",
        source_id="binance-usdm-klines-v1",
        asset_class=AssetClass.CRYPTO,
    )
    registry.register(_metadata(dataset_id, version=1, lifecycle=DatasetLifecycleState.WORKING))
    registry.register(_metadata(dataset_id, version=2, lifecycle=DatasetLifecycleState.WORKING))

    refs = list_dataset_refs(storage_root, dataset_id)
    latest = latest_dataset_ref(storage_root, dataset_id)

    assert [ref.version for ref in refs] == [1, 2]
    assert latest is not None
    assert latest.version == 2


def test_list_dataset_refs_legacy_layout(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="sample-file",
    )
    registry.register(_metadata(dataset_id, version=1, lifecycle=DatasetLifecycleState.WORKING))

    refs = list_dataset_refs(storage_root, dataset_id)

    assert [ref.version for ref in refs] == [1]
    assert refs[0].dataset_id.asset_class is None


def test_list_dataset_refs_new_layout_two_source_series_do_not_collide(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    series_a = DatasetId(
        instrument_id=Identifier("BTCUSDT.P"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="binance",
        source_id="binance-usdm-klines-v1",
        asset_class=AssetClass.CRYPTO,
    )
    series_b = replace(series_a, source_id="binance-usdm-klines-v2-backfill")
    registry.register(_metadata(series_a, version=1, lifecycle=DatasetLifecycleState.WORKING))
    registry.register(_metadata(series_b, version=1, lifecycle=DatasetLifecycleState.WORKING))

    refs_a = list_dataset_refs(storage_root, series_a)
    refs_b = list_dataset_refs(storage_root, series_b)

    assert len(refs_a) == 1
    assert len(refs_b) == 1
    assert refs_a[0].dataset_id.source_id == "binance-usdm-klines-v1"
    assert refs_b[0].dataset_id.source_id == "binance-usdm-klines-v2-backfill"


def test_latest_published_dataset_ref_new_layout(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    dataset_id = DatasetId(
        instrument_id=Identifier("BTCUSDT.P"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="binance",
        source_id="binance-usdm-klines-v1",
        asset_class=AssetClass.CRYPTO,
    )
    registry.register(_metadata(dataset_id, version=1, lifecycle=DatasetLifecycleState.WORKING))
    registry.update(_metadata(dataset_id, version=1, lifecycle=DatasetLifecycleState.PUBLISHED))
    registry.register(_metadata(dataset_id, version=2, lifecycle=DatasetLifecycleState.WORKING))

    latest_published = latest_published_dataset_ref(storage_root, dataset_id)

    assert latest_published is not None
    assert latest_published.version == 1
