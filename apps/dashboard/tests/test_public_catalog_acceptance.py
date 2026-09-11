"""End-to-end acceptance checks for the projection-backed Research Catalog."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]


def test_catalog_page_uses_projection_without_private_storage_configuration() -> None:
    app = AppTest.from_file(str(_DASHBOARD_ROOT / "Project_Overview.py"))
    app.run(timeout=30)
    app.switch_page("pages/1_Research_Catalog.py")
    app.run(timeout=30)

    assert not app.exception
    assert app.title[0].value == "Research Catalog"
    assert [metric.value for metric in app.metric] == ["0", "0", "3", "0", "4"]
    captions = " ".join(item.value for item in app.caption)
    assert "never scans the private workspace" in captions
    assert "EDITORIAL STUDY" in captions
    assert "AUTOMATIC GROUP" in captions


def test_catalog_page_source_has_no_scanner_or_path_rendering() -> None:
    source = (_DASHBOARD_ROOT / "pages" / "1_Research_Catalog.py").read_text(encoding="utf-8")

    assert "cached_list_runs" not in source
    assert "storage_fingerprint" not in source
    assert "storage_path" not in source
    assert "file://" not in source
