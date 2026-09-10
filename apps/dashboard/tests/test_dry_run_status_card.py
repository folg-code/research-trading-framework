"""Component tests for the home-page BTC dry-run status card (Sprint 062 T005).

Exercises ``render_dry_run_status_card`` end to end via Streamlit's
``AppTest`` on ``Project_Overview.py`` -- covering fresh/current, stale,
offline (unreachable), 404 (no runtime yet) and missing-config states -- so
regressions in the actual rendered page, not just the pure classifier, are
caught.
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

from dashboard_app.views import dry_run_status_card as dry_run_status_card_module
from dashboard_app.views.dry_run_status_card import (
    DRY_RUN_SIMULATION_LABELS,
    render_dry_run_status_card,
)

_PROJECT_OVERVIEW_PATH = str(Path(__file__).resolve().parents[1] / "Project_Overview.py")


class _FakeSource:
    """Stand-in for HttpLivePaperStatusDataSource -- no network involved."""

    def __init__(self, *, snapshot: dict[str, Any] | None = None, error: str | None = None) -> None:
        self._snapshot = snapshot
        self._error = error

    def fetch_session_snapshot(self, session_id: str) -> dict[str, Any]:
        del session_id
        if self._error is not None:
            raise ValueError(self._error)
        assert self._snapshot is not None
        return self._snapshot


def _fresh_snapshot() -> dict[str, Any]:
    """A snapshot with a heartbeat taken "now" so freshness never depends on
    wall-clock drift between when this module was imported and when the test
    actually runs (``render_dry_run_status_card`` has no injectable ``now``).
    """
    return {
        "schema_version": "execution.status.v1",
        "simulated": True,
        "runtime_id": "btc-futures-dry-run-vps",
        "symbol": "BTCUSDT",
        "status": "RUNNING",
        "stale": False,
        "last_heartbeat_at": datetime.now(UTC).isoformat(),
        "paper_equity": 10010.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 10.0,
        "current_position": {"quantity": "0.001"},
    }


_FRESH_SNAPSHOT = _fresh_snapshot()


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


def _run_overview(*, status_url: str | None) -> AppTest:
    with _configured_env(status_url=status_url):
        app = AppTest.from_file(_PROJECT_OVERVIEW_PATH)
        app.run(timeout=30)
    return app


def test_no_card_and_no_exception_when_status_url_is_not_configured() -> None:
    app = _run_overview(status_url=None)

    assert not app.exception
    subheaders = {entry.value for entry in app.subheader}
    assert "BTC Futures Dry-Run" not in subheaders


def test_card_renders_the_three_part_simulation_label_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import streamlit as st

    calls: list[str] = []
    monkeypatch.setattr(st, "caption", lambda text, **_kw: calls.append(text))
    monkeypatch.setattr(st, "subheader", lambda *_a, **_kw: None)
    monkeypatch.setattr(st, "columns", lambda n: [_NullMetricColumn() for _ in range(n)])
    monkeypatch.setattr(st, "page_link", lambda *_a, **_kw: None)
    monkeypatch.setattr(st, "success", lambda *_a, **_kw: None)

    from dashboard_app.config import DashboardSettings

    settings = DashboardSettings(storage_root=Path("."), status_url="http://status/status")
    render_dry_run_status_card(settings, source=_FakeSource(snapshot=_FRESH_SNAPSHOT))

    assert any(set(DRY_RUN_SIMULATION_LABELS) <= set(text.split(" · ")) for text in calls)


class _NullMetricColumn:
    def metric(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def __enter__(self) -> _NullMetricColumn:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fresh_snapshot_renders_current_status_without_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(snapshot=_FRESH_SNAPSHOT),
    )
    app = _run_overview(status_url="http://dry-run-status:8090/status")

    assert not app.exception
    subheaders = {entry.value for entry in app.subheader}
    assert "BTC Futures Dry-Run" in subheaders
    success_text = " ".join(entry.value for entry in app.success)
    assert "Running" in success_text


def test_stale_snapshot_shows_a_visible_stale_warning_not_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_snapshot = dict(_FRESH_SNAPSHOT, stale=True)
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(snapshot=stale_snapshot),
    )
    app = _run_overview(status_url="http://dry-run-status:8090/status")

    assert not app.exception
    warning_text = " ".join(entry.value for entry in app.warning)
    assert "stale" in warning_text.lower()
    success_text = " ".join(entry.value for entry in app.success)
    assert "Running" not in success_text


def test_unreachable_status_api_shows_an_explicit_offline_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(
            error="status API unreachable: [Errno 111] Connection refused"
        ),
    )
    app = _run_overview(status_url="http://dry-run-status:8090/status")

    assert not app.exception
    error_text = " ".join(entry.value for entry in app.error)
    assert "unreachable" in error_text.lower() or "offline" in error_text.lower()


def test_http_404_shows_no_runtime_state_yet_not_an_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(error="status API HTTP 404: {}"),
    )
    app = _run_overview(status_url="http://dry-run-status:8090/status")

    assert not app.exception
    warning_text = " ".join(entry.value for entry in app.warning)
    assert "no dry-run runtime state" in warning_text.lower()


def test_failed_worker_status_shows_a_failed_state_not_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_snapshot = dict(_FRESH_SNAPSHOT, status="FAILED")
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(snapshot=failed_snapshot),
    )
    app = _run_overview(status_url="http://dry-run-status:8090/status")

    assert not app.exception
    error_text = " ".join(entry.value for entry in app.error)
    assert "failed" in error_text.lower()


def test_card_links_to_the_existing_live_paper_page() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        dry_run_status_card_module,
        "HttpLivePaperStatusDataSource",
        lambda status_url: _FakeSource(snapshot=_FRESH_SNAPSHOT),
    )
    try:
        app = _run_overview(status_url="http://dry-run-status:8090/status")
    finally:
        monkeypatch.undo()

    assert not app.exception
    targets = {element.proto.page for element in app.get("page_link")}
    assert "Live_Paper_Trading" in targets
