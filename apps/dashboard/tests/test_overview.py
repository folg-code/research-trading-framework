"""Tests for Project Overview copy and diagrams."""

from __future__ import annotations

import re
from pathlib import Path

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.contracts import WorkflowKind
from dashboard_app.publication.manifest import StudyMaturity
from dashboard_app.views.overview import (
    _MATURITY_BADGE_COLOR,
    _MATURITY_DISPLAY,
    ARCHITECTURE_ONE_PAGER_URL,
    SHARED_DOMAIN_MERMAID,
    WORKFLOW_ENTRIES,
)

_POLISH_CHARS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]

#: Workflow node ids in SHARED_DOMAIN_MERMAID, keyed by title, so the
#: pipeline-shape check below can look each one up by name.
_WORKFLOW_NODE_IDS = ("marketData", "signal", "strategy", "robustness", "predictive", "execution")


def test_shared_domain_diagram_names_all_six_workflows() -> None:
    text = SHARED_DOMAIN_MERMAID
    assert "Market Data" in text
    assert "Signal Research" in text
    assert "Strategy Research" in text
    assert "Robustness Research" in text
    assert "Predictive Research" in text
    assert "Strategy Execution" in text
    assert "shared[" in text


def test_shared_domain_diagram_is_a_star_not_a_chain() -> None:
    """No workflow node may point at another workflow node -- only the shared
    node may point at a workflow, proving this is not one mandatory pipeline
    (SPRINT_059.md acceptance criteria)."""
    edge_lines = [line.strip() for line in SHARED_DOMAIN_MERMAID.splitlines() if "-->" in line]
    assert edge_lines, "expected at least one edge in the diagram"
    for line in edge_lines:
        source, _, target = line.partition("-->")
        source = source.strip()
        target = target.strip()
        assert source == "shared", f"unexpected edge source (not the shared hub): {line!r}"
        assert any(target.startswith(node_id) for node_id in _WORKFLOW_NODE_IDS), (
            f"unexpected edge target: {line!r}"
        )


def test_workflow_entries_cover_all_six_workflows_with_real_pages() -> None:
    assert len(WORKFLOW_ENTRIES) == 6
    assert {entry.workflow for entry in WORKFLOW_ENTRIES} == {
        WorkflowKind.MARKET,
        WorkflowKind.SIGNAL,
        WorkflowKind.STRATEGY,
        WorkflowKind.ROBUSTNESS,
        WorkflowKind.PREDICTIVE,
        WorkflowKind.LIVE_PAPER,
    }
    for entry in WORKFLOW_ENTRIES:
        assert isinstance(entry.maturity, StudyMaturity)
        page_path = _DASHBOARD_ROOT / entry.page_path
        assert page_path.is_file(), f"{entry.title} points at a missing page: {entry.page_path}"


def test_strategy_execution_is_in_development_not_as_built() -> None:
    """ADR-0021: Strategy Execution remains a future capability -- the
    dashboard must not claim it is fully shipped."""
    execution_entries = [e for e in WORKFLOW_ENTRIES if e.workflow is WorkflowKind.LIVE_PAPER]
    assert len(execution_entries) == 1
    assert execution_entries[0].maturity == StudyMaturity.IN_DEVELOPMENT


def test_maturity_badge_mapping_covers_all_four_values_with_distinct_colors() -> None:
    assert set(_MATURITY_DISPLAY) == set(StudyMaturity)
    assert set(_MATURITY_BADGE_COLOR) == set(StudyMaturity)
    assert len(set(_MATURITY_BADGE_COLOR.values())) == 4, "each maturity needs its own color"
    assert _MATURITY_DISPLAY[StudyMaturity.AS_BUILT] == "AS BUILT"
    assert _MATURITY_DISPLAY[StudyMaturity.IN_DEVELOPMENT] == "IN DEVELOPMENT"
    assert _MATURITY_DISPLAY[StudyMaturity.FUTURE_IDEAS] == "FUTURE IDEAS"
    assert _MATURITY_DISPLAY[StudyMaturity.ARCHIVED] == "ARCHIVED"


def test_portfolio_overview_content_loads_and_is_well_formed() -> None:
    document = load_content_document(content_document_path("portfolio-overview"))

    assert not isinstance(document, ContentUnavailable)
    assert document.slug == "portfolio-overview"
    assert document.status == StudyMaturity.AS_BUILT
    assert "github.com/folg-code/research-trading-framework" in document.body_markdown
    assert (
        "simplified" in document.body_markdown.lower()
        or "read-only" in document.body_markdown.lower()
    )


def test_architecture_one_pager_exists_and_is_linked() -> None:
    one_pager = _DASHBOARD_ROOT / "docs" / "ARCHITECTURE.md"
    assert one_pager.is_file()
    text = one_pager.read_text(encoding="utf-8")
    assert "Six independent workflows" in text
    assert "src/" in text
    assert "user_data" in text or "user space" in text
    assert "Live paper path" in text
    assert "apps/dashboard/docs/ARCHITECTURE.md" in ARCHITECTURE_ONE_PAGER_URL


def test_overview_modules_are_english_only() -> None:
    overview = _DASHBOARD_ROOT / "src" / "dashboard_app" / "views" / "overview.py"
    home = _DASHBOARD_ROOT / "Project_Overview.py"
    one_pager = _DASHBOARD_ROOT / "docs" / "ARCHITECTURE.md"
    content = _DASHBOARD_ROOT / "content" / "portfolio-overview.md"
    for path in (overview, home, one_pager, content):
        text = path.read_text(encoding="utf-8")
        assert _POLISH_CHARS.search(text) is None, f"Polish characters found in {path.name}"
        assert "Analiza" not in text
        assert "Wyniki" not in text
        assert "Bieżący" not in text
