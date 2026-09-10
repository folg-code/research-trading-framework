"""Contract tests for Sprint 061 portfolio content and Home structure."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.publication.manifest import StudyMaturity
from dashboard_app.views.overview import (
    FEATURED_STUDIES,
    FUTURE_IDEAS,
    RECENT_NOTES,
    WORKFLOW_ENTRIES,
)

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _DASHBOARD_ROOT.parents[1]
_OVERVIEW_PATH = str(_DASHBOARD_ROOT / "Project_Overview.py")

_CONTENT_STATUS = {
    "architecture": StudyMaturity.AS_BUILT,
    "engineering": StudyMaturity.AS_BUILT,
    "future-direction": StudyMaturity.FUTURE_IDEAS,
    "future-ai-research-infrastructure": StudyMaturity.FUTURE_IDEAS,
    "future-research-application": StudyMaturity.FUTURE_IDEAS,
    "research-engineering-notes": StudyMaturity.AS_BUILT,
    "workflow-market-data": StudyMaturity.AS_BUILT,
    "workflow-signal-research": StudyMaturity.AS_BUILT,
    "workflow-strategy-research": StudyMaturity.AS_BUILT,
    "workflow-robustness-research": StudyMaturity.AS_BUILT,
    "workflow-predictive-research": StudyMaturity.AS_BUILT,
    "workflow-strategy-execution": StudyMaturity.IN_DEVELOPMENT,
}


def _run_overview() -> AppTest:
    with tempfile.TemporaryDirectory() as storage_root:
        os.environ["DASHBOARD_STORAGE_ROOT"] = storage_root
        try:
            app = AppTest.from_file(_OVERVIEW_PATH)
            app.run(timeout=30)
        finally:
            del os.environ["DASHBOARD_STORAGE_ROOT"]
    return app


def _switch_to(page_path: str) -> AppTest:
    app = _run_overview()
    with tempfile.TemporaryDirectory() as storage_root:
        os.environ["DASHBOARD_STORAGE_ROOT"] = storage_root
        try:
            app.switch_page(page_path)
            app.run(timeout=30)
        finally:
            del os.environ["DASHBOARD_STORAGE_ROOT"]
    return app


def test_sprint061_documents_load_and_link_to_repository_sources() -> None:
    for slug, expected_status in _CONTENT_STATUS.items():
        document = load_content_document(content_document_path(slug))
        assert not isinstance(document, ContentUnavailable), f"{slug}: {document}"
        assert document.status is expected_status
        for link in document.links:
            assert (_REPO_ROOT / link).is_file(), f"{slug} links to missing source: {link}"


def test_future_ideas_state_non_implementation_and_approval_limits() -> None:
    ai = load_content_document(content_document_path("future-ai-research-infrastructure"))
    app = load_content_document(content_document_path("future-research-application"))
    assert not isinstance(ai, ContentUnavailable)
    assert not isinstance(app, ContentUnavailable)

    ai_text = ai.body_markdown.lower()
    assert "not implemented" in ai_text
    assert "provider selection" in ai_text and "undecided" in ai_text
    assert "no unofficial browser automation" in ai_text
    assert "never promote itself into live execution" in ai_text

    app_text = app.body_markdown.lower()
    assert "draft" in app_text
    assert "no ui stack or sprint is approved" in app_text
    assert "second research" in app_text
    assert "public" in app_text and "command surface" in app_text


def test_home_uses_two_featured_studies_three_notes_and_exactly_two_future_ideas() -> None:
    assert len(FEATURED_STUDIES) == 2
    assert len(RECENT_NOTES) == 3
    assert [entry.title for entry in FUTURE_IDEAS] == [
        "AI Research Infrastructure",
        "Research Application",
    ]

    app = _run_overview()
    assert not app.exception
    subheaders = [element.value for element in app.subheader]
    assert all(entry.title in subheaders for entry in FEATURED_STUDIES)
    assert all(entry.title in subheaders for entry in RECENT_NOTES)
    assert all(entry.title in subheaders for entry in FUTURE_IDEAS)


def test_home_section_order_keeps_catalog_after_studies_notes_and_future_direction() -> None:
    app = _run_overview()
    headers = [element.value for element in app.header]
    assert headers == [
        "Featured studies",
        "Research & Engineering Notes",
        "Future direction",
        "Complete research catalog",
    ]


def test_home_links_every_stable_sprint061_page() -> None:
    app = _run_overview()
    targets = {element.proto.page for element in app.get("page_link")}
    for expected in (
        "Architecture",
        "Engineering",
        "Future_Direction",
        "AI_Research_Infrastructure",
        "Research_Application",
        "Research_and_Engineering_Notes",
    ):
        assert expected in targets


def test_workflow_cards_lead_to_publications_before_technical_evidence() -> None:
    expected_pages = {
        "Market Data": "pages/16_Market_Data_Workflow.py",
        "Signal Research": "pages/17_Signal_Research_Workflow.py",
        "Strategy Research": "pages/18_Strategy_Research_Workflow.py",
        "Robustness Research": "pages/19_Robustness_Research_Workflow.py",
        "Predictive Research": "pages/20_Predictive_Research_Workflow.py",
        "Strategy Execution": "pages/21_Strategy_Execution_Workflow.py",
    }
    assert {entry.title: entry.page_path for entry in WORKFLOW_ENTRIES} == expected_pages

    app = _run_overview()
    targets = {element.proto.page for element in app.get("page_link")}
    for page_path in expected_pages.values():
        assert Path(page_path).stem.split("_", maxsplit=1)[1] in targets


def test_supporting_pages_render_with_stable_titles() -> None:
    pages = {
        "pages/10_Architecture.py": "Architecture",
        "pages/11_Engineering.py": "Engineering",
        "pages/12_Future_Direction.py": "Future Direction",
        "pages/13_AI_Research_Infrastructure.py": "AI Research Infrastructure",
        "pages/14_Research_Application.py": "Research Application",
        "pages/15_Research_and_Engineering_Notes.py": "Research & Engineering Notes",
        "pages/16_Market_Data_Workflow.py": "Market Data Workflow",
        "pages/17_Signal_Research_Workflow.py": "Signal Research Workflow",
        "pages/18_Strategy_Research_Workflow.py": "Strategy Research Workflow",
        "pages/19_Robustness_Research_Workflow.py": "Robustness Research Workflow",
        "pages/20_Predictive_Research_Workflow.py": "Predictive Research Workflow",
        "pages/21_Strategy_Execution_Workflow.py": "Strategy Execution Workflow",
    }
    for page_path, expected_title in pages.items():
        app = _switch_to(page_path)
        assert not app.exception
        assert app.title[0].value == expected_title


def test_workflow_publications_offer_evidence_only_after_methodology() -> None:
    evidence_targets = {
        "pages/16_Market_Data_Workflow.py": "Market_and_Signal_Research",
        "pages/17_Signal_Research_Workflow.py": "Market_and_Signal_Research",
        "pages/18_Strategy_Research_Workflow.py": "Strategy_Research",
        "pages/19_Robustness_Research_Workflow.py": "Robustness_Analysis",
        "pages/20_Predictive_Research_Workflow.py": "Predictive_Research",
        "pages/21_Strategy_Execution_Workflow.py": "Live_Paper_Trading",
    }
    for publication_page, technical_target in evidence_targets.items():
        app = _switch_to(publication_page)
        assert not app.exception
        assert "Explore Evidence" in [element.value for element in app.subheader]
        targets = {element.proto.page for element in app.get("page_link")}
        assert technical_target in targets
