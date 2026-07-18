"""Tests for dashboard configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from dashboard_app.config import (
    DEFAULT_LIVE_PAPER_STATUS_URL,
    load_settings,
    storage_root_status,
)


def test_load_settings_from_explicit_path(tmp_path: Path) -> None:
    market = tmp_path / "market_data"
    research = tmp_path / "research"
    market.mkdir()
    research.mkdir()

    settings = load_settings(storage_root=tmp_path)

    assert settings.storage_root == tmp_path.resolve()
    assert settings.status_url == DEFAULT_LIVE_PAPER_STATUS_URL
    assert storage_root_status(settings) == {
        "storage_root_exists": True,
        "market_data_exists": True,
        "research_exists": True,
    }


def test_load_settings_requires_env_when_unspecified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DASHBOARD_STORAGE_ROOT", raising=False)
    with pytest.raises(ValueError, match="DASHBOARD_STORAGE_ROOT"):
        load_settings()


def test_load_settings_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHBOARD_STORAGE_ROOT", str(tmp_path))
    monkeypatch.delenv("DASHBOARD_STATUS_URL", raising=False)
    settings = load_settings()
    assert settings.storage_root == tmp_path.resolve()
    assert settings.status_url == DEFAULT_LIVE_PAPER_STATUS_URL


def test_load_settings_reads_status_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHBOARD_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("DASHBOARD_STATUS_URL", "https://example.test/status")
    settings = load_settings()
    assert settings.status_url == "https://example.test/status"


def test_load_settings_status_url_override(tmp_path: Path) -> None:
    settings = load_settings(
        storage_root=tmp_path,
        status_url=" https://override.test/status ",
    )
    assert settings.status_url == "https://override.test/status"
