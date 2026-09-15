"""HTTP contract tests for POST /api/v1/validate (Sprint 064 T008)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig


def test_validate_bad_definition_returns_ok_false_with_frameworks_error(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/validate",
                json={
                    "definition": {
                        "research_id": "workbench_endpoint_test",
                        "research_scope": "SIGNAL_MODEL_ONLY",
                        "dataset_ref": "not-a-real-dataset-ref",
                        "time_range": {"start": "2018-12-31", "end": "2018-12-31"},
                        "horizons": ["5m"],
                        "signal_model": "higher_low_long",
                        "baseline": {"type": "AFTER_SIGNAL"},
                    }
                },
            )
            assert response.status == 200
            payload = await response.json()
            assert payload["ok"] is False
            assert payload["plan"] is None
            assert payload["error_message"]
        finally:
            await client.close()

    asyncio.run(_run())


def test_validate_missing_definition_is_400(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/v1/validate", json={})
            assert response.status == 400
        finally:
            await client.close()

    asyncio.run(_run())
