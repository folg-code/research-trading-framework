"""Tests for public dashboard chrome helpers."""

from __future__ import annotations

from pathlib import Path

from dashboard_app.ui import mask_status_url


def test_mask_status_url_hides_path() -> None:
    assert mask_status_url("https://example.test/status/secret") == "https://example.test/…"
    assert mask_status_url(None) == "—"
    assert mask_status_url("") == "—"


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
    assert "render_shared_domain_map" in home_text
    assert "render_workflow_entries" in home_text
    assert "DASHBOARD_STORAGE_ROOT" not in home_text
    assert "pages/1_Research_Catalog.py" in overview_text
    assert "st.mermaid_chart" in overview_text


def test_public_chrome_does_not_expose_workspace_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    chrome = (root / "src/dashboard_app/ui.py").read_text(encoding="utf-8")

    assert "DASHBOARD_STORAGE_ROOT" not in chrome
    assert "Workspace root" not in chrome
    assert "storage_root" not in chrome
    assert "load_projection_bundle_from_path" in chrome
