"""Contract tests for the saved-definition list/save/load endpoints (Sprint 064 T008)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.definitions_store import (
    InvalidDefinitionNameError,
    definition_path,
    list_definition_names,
    load_definition,
    save_definition,
)

_DEFINITION = {
    "research_id": "workbench_saved_study",
    "research_scope": "SIGNAL_MODEL_ONLY",
    "dataset_ref": "ES.c.0|ohlcv|1m|csv|test@1",
    "time_range": {"start": "2024-01-01", "end": "2024-01-02"},
    "horizons": ["5m"],
    "signal_model": "higher_low_long",
}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    path = save_definition(tmp_path, "my-study", _DEFINITION)

    assert path == definition_path(tmp_path, "my-study")
    assert path.is_file()
    assert load_definition(tmp_path, "my-study") == _DEFINITION


def test_list_definition_names_sorted(tmp_path: Path) -> None:
    save_definition(tmp_path, "zeta", _DEFINITION)
    save_definition(tmp_path, "alpha", _DEFINITION)

    assert list_definition_names(tmp_path) == ("alpha", "zeta")


def test_list_definition_names_empty_root(tmp_path: Path) -> None:
    assert list_definition_names(tmp_path) == ()


def test_save_rejects_unsafe_name(tmp_path: Path) -> None:
    with pytest.raises(InvalidDefinitionNameError):
        save_definition(tmp_path, "../escape", _DEFINITION)


def test_definitions_http_contract(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            empty_response = await client.get("/api/v1/definitions")
            assert (await empty_response.json())["definitions"] == []

            save_response = await client.post(
                "/api/v1/definitions", json={"name": "my-study", "definition": _DEFINITION}
            )
            assert save_response.status == 201
            saved = await save_response.json()
            assert saved["name"] == "my-study"
            assert saved["path"]

            list_response = await client.get("/api/v1/definitions")
            assert (await list_response.json())["definitions"] == ["my-study"]

            load_response = await client.get("/api/v1/definitions/my-study")
            assert load_response.status == 200
            loaded = await load_response.json()
            assert loaded["definition"] == _DEFINITION

            missing_response = await client.get("/api/v1/definitions/does-not-exist")
            assert missing_response.status == 404
        finally:
            await client.close()

    asyncio.run(_run())


def test_save_missing_fields_is_400(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/v1/definitions", json={"name": "x"})
            assert response.status == 400
        finally:
            await client.close()

    asyncio.run(_run())
