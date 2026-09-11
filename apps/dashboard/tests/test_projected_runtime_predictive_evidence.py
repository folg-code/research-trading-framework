"""Acceptance checks for bounded Strategy Execution and Predictive evidence."""

from __future__ import annotations

import os
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard_app.views.live_paper import sanitize_public_live_paper_snapshot

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]


def test_live_paper_snapshot_allowlist_excludes_internal_and_unknown_fields() -> None:
    public = sanitize_public_live_paper_snapshot(
        {
            "status": "running",
            "simulated": True,
            "symbol": "BTCUSDT",
            "feed_last_error": "C:/private/runtime.log",
            "storage_path": "C:/private/workspace",
            "recent_orders": [{"order_id": "secret"}],
            "current_position": {
                "side": "long",
                "quantity": 1,
                "account_id": "private-account",
            },
            "recent_bars": [
                {
                    "observed_at": "2026-09-10T00:00:00+00:00",
                    "open": 1,
                    "high": 2,
                    "low": 1,
                    "close": 2,
                    "provider_debug": "private",
                }
            ],
        }
    )

    assert public["status"] == "running"
    assert public["current_position"] == {"side": "long", "quantity": 1}
    assert public["recent_bars"] == [
        {
            "observed_at": "2026-09-10T00:00:00+00:00",
            "open": 1,
            "high": 2,
            "low": 1,
            "close": 2,
        }
    ]
    for forbidden in ("storage_path", "recent_orders", "feed_last_error", "account_id"):
        assert forbidden not in repr(public)


def test_pages_5_and_6_render_without_workspace_configuration() -> None:
    previous_storage = os.environ.pop("DASHBOARD_STORAGE_ROOT", None)
    previous_status = os.environ.pop("DASHBOARD_STATUS_URL", None)
    try:
        app = AppTest.from_file(str(_DASHBOARD_ROOT / "Project_Overview.py"))
        app.run(timeout=30)

        app.switch_page("pages/5_Live_Paper_Trading.py")
        app.run(timeout=30)
        assert not app.exception
        assert app.title[0].value == "Strategy Execution Evidence"
        assert "LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS" in (
            item.value for item in app.warning
        )

        app.switch_page("pages/6_Predictive_Research.py")
        app.run(timeout=30)
        assert not app.exception
        assert app.title[0].value == "Predictive Research Evidence"
        assert len(app.get("plotly_chart")) == 1
    finally:
        if previous_storage is not None:
            os.environ["DASHBOARD_STORAGE_ROOT"] = previous_storage
        if previous_status is not None:
            os.environ["DASHBOARD_STATUS_URL"] = previous_status


def test_pages_5_and_6_have_no_private_artifact_read_path() -> None:
    forbidden = (
        "DASHBOARD_STORAGE_ROOT",
        "settings.storage_root",
        "storage_fingerprint",
        "storage_path",
        "file://",
        "cached_list_predictive_catalog",
        "load_run_metrics",
        "load_run_provenance",
        "report_html_path",
        "st.json",
        "Raw snapshot",
    )
    for name in ("5_Live_Paper_Trading.py", "6_Predictive_Research.py"):
        source = (_DASHBOARD_ROOT / "pages" / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
