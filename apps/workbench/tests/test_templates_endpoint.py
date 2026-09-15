"""Contract tests for GET /api/v1/templates and POST .../apply (Sprint 064 T008)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.templates_endpoint import build_templates_response

_FRAMEWORK_TEMPLATE_IDS = {
    "minimal-single-signal",
    "multi-horizon-baseline",
    "quality-rules-strict",
}


def test_build_templates_response_lists_framework_templates(tmp_path: Path) -> None:
    body = build_templates_response(WorkbenchApiConfig(storage_root=tmp_path))

    ids = {template["template_id"] for template in body["templates"]}
    assert ids == _FRAMEWORK_TEMPLATE_IDS
    for template in body["templates"]:
        assert template["status"] == "SUPPORTED"
        assert "path" not in template


def test_templates_and_apply_http_contract(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            list_response = await client.get("/api/v1/templates")
            assert list_response.status == 200
            listed = await list_response.json()
            assert {t["template_id"] for t in listed["templates"]} == _FRAMEWORK_TEMPLATE_IDS

            apply_response = await client.post(
                "/api/v1/templates/minimal-single-signal/apply",
                json={
                    "overrides": {
                        "research_id": "workbench_test_study",
                        "dataset_ref": "ES.c.0|ohlcv|1m|csv|test@1",
                        "time_range": {"start": "2024-01-01", "end": "2024-01-02"},
                    }
                },
            )
            assert apply_response.status == 200
            applied = await apply_response.json()
            assert applied["definition"]["research_id"] == "workbench_test_study"
        finally:
            await client.close()

    asyncio.run(_run())


def test_apply_unknown_template_is_404(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post(
                "/api/v1/templates/does-not-exist/apply", json={"overrides": {}}
            )
            assert response.status == 404
        finally:
            await client.close()

    asyncio.run(_run())
