"""Contract test for GET /api/v1/models (T008 model picker)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.models_endpoint import build_models_response


def test_build_models_response_lists_both_kinds() -> None:
    body = build_models_response()

    assert "high_volatility" in body["market_models"]
    assert "higher_low_long" in body["signal_models"]


def test_models_http_contract(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/models")
            assert response.status == 200
            payload = await response.json()
            assert "high_volatility" in payload["market_models"]
            assert "higher_low_long" in payload["signal_models"]
        finally:
            await client.close()

    asyncio.run(_run())
