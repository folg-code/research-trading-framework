"""Tests for Project Overview copy and diagrams."""

from __future__ import annotations

import re
from pathlib import Path

from dashboard_app.views.overview import (
    ARCHITECTURE_ONE_PAGER_URL,
    CAPABILITIES_MERMAID,
    LIVE_WORKFLOW_MERMAID,
    RESEARCH_WORKFLOW_MERMAID,
)

_POLISH_CHARS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]


def test_research_diagram_covers_provider_to_analytics() -> None:
    text = RESEARCH_WORKFLOW_MERMAID
    assert "Data provider" in text
    assert "Framework normalization" in text
    assert "Normalized DatasetRef" in text
    assert "Market and signal models" in text
    assert "Persisted research storage" in text
    assert "Analytics layer" in text


def test_live_diagram_covers_aws_and_readonly_dashboard() -> None:
    text = LIVE_WORKFLOW_MERMAID
    assert "Exchange provider live feed" in text
    assert "subgraph aws" in text
    assert "Framework runtime" in text
    assert "Live strategy instance" in text
    assert "Research path" not in text
    assert "Read-only status API" in text
    assert "Dashboard Live Paper view" in text


def test_capabilities_diagram_keeps_research_and_execution_independent() -> None:
    text = CAPABILITIES_MERMAID
    assert "Signal Research" in text
    assert "Strategy Research" in text
    assert "Strategy Execution" in text
    assert "Shared definitions" in text


def test_architecture_one_pager_exists_and_is_linked() -> None:
    one_pager = _DASHBOARD_ROOT / "docs" / "ARCHITECTURE.md"
    assert one_pager.is_file()
    text = one_pager.read_text(encoding="utf-8")
    assert "Three independent capabilities" in text
    assert "src/" in text
    assert "user_data" in text or "user space" in text
    assert "Live paper path" in text
    assert "apps/dashboard/docs/ARCHITECTURE.md" in ARCHITECTURE_ONE_PAGER_URL

    overview = _DASHBOARD_ROOT / "src" / "dashboard_app" / "views" / "overview.py"
    home = _DASHBOARD_ROOT / "Project_Overview.py"
    overview_text = overview.read_text(encoding="utf-8")
    home_text = home.read_text(encoding="utf-8")
    assert "render_architecture_one_pager" in home_text
    assert ARCHITECTURE_ONE_PAGER_URL in overview_text
    assert "architecture one-pager" in home_text.lower()


def test_overview_mentions_simplified_workflow_and_github_readme() -> None:
    overview = _DASHBOARD_ROOT / "src" / "dashboard_app" / "views" / "overview.py"
    home = _DASHBOARD_ROOT / "Project_Overview.py"
    overview_text = overview.read_text(encoding="utf-8")
    home_text = home.read_text(encoding="utf-8")
    assert "simplified" in overview_text.lower()
    assert "github.com/folg-code/research-trading-framework" in overview_text
    assert "simplified" in home_text.lower()
    assert "github.com/folg-code/research-trading-framework" in home_text


def test_overview_modules_are_english_only() -> None:
    overview = _DASHBOARD_ROOT / "src" / "dashboard_app" / "views" / "overview.py"
    home = _DASHBOARD_ROOT / "Project_Overview.py"
    one_pager = _DASHBOARD_ROOT / "docs" / "ARCHITECTURE.md"
    for path in (overview, home, one_pager):
        text = path.read_text(encoding="utf-8")
        assert _POLISH_CHARS.search(text) is None, f"Polish characters found in {path.name}"
        assert "Analiza" not in text
        assert "Wyniki" not in text
        assert "Bieżący" not in text
