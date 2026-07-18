"""Tests for Project Overview copy and diagrams."""

from __future__ import annotations

import re
from pathlib import Path

from dashboard_app.views.overview import (
    LIVE_WORKFLOW_MERMAID,
    RESEARCH_WORKFLOW_MERMAID,
)

_POLISH_CHARS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


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
    assert "AWS" in text
    assert "same contract — not the same instance" in text
    assert "Read-only status API" in text
    assert "Dashboard Live Paper view" in text


def test_overview_modules_are_english_only() -> None:
    overview = (
        Path(__file__).resolve().parents[1] / "src" / "dashboard_app" / "views" / "overview.py"
    )
    home = Path(__file__).resolve().parents[1] / "Project_Overview.py"
    for path in (overview, home):
        text = path.read_text(encoding="utf-8")
        assert _POLISH_CHARS.search(text) is None, f"Polish characters found in {path.name}"
        assert "Analiza" not in text
        assert "Wyniki" not in text
        assert "Bieżący" not in text
