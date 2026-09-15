"""Contract test for GET /api/v1/datasets (Sprint 064 T004)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.time.models.timeframe import Timeframe

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.datasets_endpoint import build_datasets_response

_START_AT = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
_END_AT = datetime(2024, 1, 1, 13, 0, tzinfo=UTC)


def _dataset_ref(instrument: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(instrument),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
        ),
        version=1,
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


def test_build_datasets_response_returns_only_published(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    published_ref = _dataset_ref("ES.c.0")
    registry.register(_metadata(published_ref, lifecycle=DatasetLifecycleState.WORKING))
    registry.update(_metadata(published_ref, lifecycle=DatasetLifecycleState.PUBLISHED))
    working_ref = _dataset_ref("NQ.c.0")
    registry.register(_metadata(working_ref, lifecycle=DatasetLifecycleState.WORKING))

    body = build_datasets_response(WorkbenchApiConfig(storage_root=tmp_path))

    assert body["schema_version"] == WORKBENCH_API_VERSION
    assert len(body["datasets"]) == 1
    entry = body["datasets"][0]
    assert entry["dataset_ref"] == str(published_ref)
    assert entry["instrument_id"] == "ES.c.0"
    assert entry["row_count"] == 42
    # No filesystem path in the response (ADR-0037 section 4).
    assert "path" not in entry
    assert "checksum" not in entry


def test_datasets_endpoint_http_contract(tmp_path: Path) -> None:
    registry = FileDatasetRegistry(tmp_path)
    published_ref = _dataset_ref("ES.c.0")
    registry.register(_metadata(published_ref, lifecycle=DatasetLifecycleState.WORKING))
    registry.update(_metadata(published_ref, lifecycle=DatasetLifecycleState.PUBLISHED))

    async def _run() -> None:
        app = create_app(WorkbenchApiConfig(storage_root=tmp_path))
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/datasets")
            assert response.status == 200
            payload = await response.json()
            assert payload["schema_version"] == WORKBENCH_API_VERSION
            assert len(payload["datasets"]) == 1
            assert payload["datasets"][0]["instrument_id"] == "ES.c.0"
        finally:
            await client.close()

    asyncio.run(_run())


def test_datasets_endpoint_empty_storage_root(tmp_path: Path) -> None:
    body = build_datasets_response(WorkbenchApiConfig(storage_root=tmp_path / "does-not-exist"))
    assert body == {"schema_version": WORKBENCH_API_VERSION, "datasets": []}
