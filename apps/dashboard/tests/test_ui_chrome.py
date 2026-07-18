"""Tests for public dashboard chrome helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from dashboard_app.ui import env_storage_configured, mask_status_url


def test_mask_status_url_hides_path() -> None:
    assert mask_status_url("https://example.test/status/secret") == "https://example.test/…"
    assert mask_status_url(None) == "—"
    assert mask_status_url("") == "—"


def test_env_storage_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DASHBOARD_STORAGE_ROOT", raising=False)
    assert env_storage_configured() is False
    monkeypatch.setenv("DASHBOARD_STORAGE_ROOT", str(Path.cwd()))
    assert env_storage_configured() is True


def test_home_module_has_no_mvp_or_duckdb_copy() -> None:
    root = Path(__file__).resolve().parents[1]
    home = root / "Project_Overview.py"
    overview = root / "src" / "dashboard_app" / "views" / "overview.py"
    home_text = home.read_text(encoding="utf-8")
    overview_text = overview.read_text(encoding="utf-8")
    assert home.name == "Project_Overview.py"
    assert "MVP pages" not in home_text
    assert "DuckDB" not in home_text
    assert "Parquet" not in home_text
    assert "render_origin_of_results" in home_text
    assert "pages/1_Research_Catalog.py" in overview_text
    assert "st.mermaid_chart" in overview_text
