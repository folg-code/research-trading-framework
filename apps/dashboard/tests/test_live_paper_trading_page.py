"""Regression tests for ``pages/5_Live_Paper_Trading.py`` (Sprint 062 T005).

Guards against the "runtime status unavailable" placeholder copy being shown
even when the status endpoint *is* configured -- SPRINT_062.md T005's
acceptance criterion requires the placeholder to disappear once the endpoint
is configured, and for stale/offline/failed states to still be shown
honestly.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import dashboard_app.datasources as datasources_module

_PAGE_PATH = str(Path(__file__).resolve().parents[1] / "pages" / "5_Live_Paper_Trading.py")

_MIGRATION_BANNER_TEXT = "No stale snapshot is substituted"


class _FakeSource:
    def __init__(self, *, snapshot: dict[str, Any]) -> None:
        self._snapshot = snapshot

    def fetch_session_snapshot(self, session_id: str) -> dict[str, Any]:
        del session_id
        return self._snapshot


@contextmanager
def _configured_env(*, status_url: str | None) -> Iterator[None]:
    with tempfile.TemporaryDirectory() as storage_root:
        os.environ["DASHBOARD_STORAGE_ROOT"] = storage_root
        if status_url is not None:
            os.environ["DASHBOARD_STATUS_URL"] = status_url
        try:
            yield
        finally:
            del os.environ["DASHBOARD_STORAGE_ROOT"]
            os.environ.pop("DASHBOARD_STATUS_URL", None)


def _page_text(app: AppTest) -> str:
    chunks: list[str] = []
    for collection in (app.info, app.warning, app.error, app.caption, app.markdown):
        chunks.extend(str(entry.value) for entry in collection)
    return " ".join(chunks)


def test_migration_banner_shown_when_status_url_is_not_configured() -> None:
    with _configured_env(status_url=None):
        app = AppTest.from_file(_PAGE_PATH)
        app.run(timeout=30)

    assert not app.exception
    assert _MIGRATION_BANNER_TEXT in _page_text(app)


def test_migration_banner_removed_once_status_url_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = {
        "schema_version": "execution.status.v1",
        "simulated": True,
        "symbol": "BTCUSDT",
        "status": "RUNNING",
        "stale": False,
        "last_heartbeat_at": datetime.now(UTC).isoformat(),
        "paper_equity": 10010.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 10.0,
        "current_position": None,
    }
    monkeypatch.setattr(
        datasources_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(snapshot=snapshot),
    )

    with _configured_env(status_url="http://dry-run-status:8090/status"):
        app = AppTest.from_file(_PAGE_PATH)
        app.run(timeout=30)

    assert not app.exception
    assert _MIGRATION_BANNER_TEXT not in _page_text(app)
