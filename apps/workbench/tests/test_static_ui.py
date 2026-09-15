"""Tests for serving workbench_ui's static export (Sprint 064 T008, ADR-0044).

Uses a tiny synthetic `out/` directory rather than depending on a real
`npm run build` -- `create_app`'s `ui_dist_dir` override is exactly this
test-only seam, same pattern as `cli_command`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig


def _build_fake_export(tmp_path: Path) -> Path:
    dist_dir = tmp_path / "out"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<html>home</html>", encoding="utf-8")
    (dist_dir / "jobs.html").write_text("<html>jobs</html>", encoding="utf-8")
    next_dir = dist_dir / "_next" / "static"
    next_dir.mkdir(parents=True)
    (next_dir / "app.js").write_text("console.log('app');", encoding="utf-8")
    return dist_dir


def test_serves_index_at_root(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/")
            assert response.status == 200
            assert "home" in await response.text()
        finally:
            await client.close()

    asyncio.run(_run())


def test_serves_extensionless_route_from_its_html_file(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/jobs")
            assert response.status == 200
            assert "jobs" in await response.text()

            # A query string (?id=...) must not affect file resolution.
            queried = await client.get("/jobs?id=abc123")
            assert queried.status == 200
        finally:
            await client.close()

    asyncio.run(_run())


def test_serves_nested_static_asset(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/_next/static/app.js")
            assert response.status == 200
            assert "console.log" in await response.text()
        finally:
            await client.close()

    asyncio.run(_run())


def test_unknown_path_is_404(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/does/not/exist")
            assert response.status == 404
        finally:
            await client.close()

    asyncio.run(_run())


def test_path_traversal_is_refused(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("do not serve me", encoding="utf-8")
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/../secret.txt")
            assert response.status in (400, 404)
        finally:
            await client.close()

    asyncio.run(_run())


def test_missing_build_is_404_with_helpful_message(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=tmp_path / "does-not-exist")
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/")
            assert response.status == 404
            assert "npm run build" in await response.text()
        finally:
            await client.close()

    asyncio.run(_run())


def test_api_routes_still_win_over_the_static_catch_all(tmp_path: Path) -> None:
    dist_dir = _build_fake_export(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path / "workspace")

    async def _run() -> None:
        app = create_app(config, ui_dist_dir=dist_dir)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/datasets")
            assert response.status == 200
            payload = await response.json()
            assert "datasets" in payload
        finally:
            await client.close()

    asyncio.run(_run())
