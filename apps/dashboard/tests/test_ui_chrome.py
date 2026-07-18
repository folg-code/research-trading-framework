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
    home = Path(__file__).resolve().parents[1] / "app.py"
    text = home.read_text(encoding="utf-8")
    assert "MVP pages" not in text
    assert "DuckDB" not in text
    assert "Parquet" not in text
    assert "Project Overview" in text or "Trading Research Framework" in text
    assert "pages/1_Research_Catalog.py" in text
