"""Tests for dashboard configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from dashboard_app.config import load_settings, storage_root_status


def test_load_settings_from_explicit_path(tmp_path: Path) -> None:
    market = tmp_path / "market_data"
    research = tmp_path / "research"
    market.mkdir()
    research.mkdir()

    settings = load_settings(storage_root=tmp_path)

    assert settings.storage_root == tmp_path.resolve()
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
    settings = load_settings()
    assert settings.storage_root == tmp_path.resolve()
