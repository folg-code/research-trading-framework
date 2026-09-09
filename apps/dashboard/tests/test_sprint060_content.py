"""Tests for Sprint 060 T002's workflow-context and methodology content.

D060-02 requires Signal Research and Predictive Research to be presented
as separate processes, never a synthetic end-to-end pipeline; the
methodology page must be living, run-agnostic content with no
run-specific interpretation. These tests prove both documents load
cleanly and mechanically confirm no run-specific fact leaked in.
"""

from __future__ import annotations

from pathlib import Path

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.publication.manifest import StudyMaturity

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]

#: Facts specific to the real BTC Signal Quality study run -- none of
#: these belong in general workflow/methodology content (that is T003's
#: study page, sourced from the publication/ projection).
_RUN_SPECIFIC_STRINGS = (
    "2ef6426b3cc06463",  # the run id
    "437f6b7f9240208f",  # the dataset id
    "INCONCLUSIVE",  # this run's persisted verdict
    "0.5239",  # this run's pooled ROC AUC
)

_CONTENT_SLUGS = ("signal-predictive-workflow-context", "signal-quality-methodology")


def test_content_documents_load_cleanly() -> None:
    for slug in _CONTENT_SLUGS:
        document = load_content_document(content_document_path(slug))

        assert not isinstance(document, ContentUnavailable), f"{slug} failed to load: {document}"
        assert document.slug == slug
        assert document.status == StudyMaturity.AS_BUILT


def test_content_links_point_to_real_files() -> None:
    repo_root = _DASHBOARD_ROOT.parents[1]
    for slug in _CONTENT_SLUGS:
        document = load_content_document(content_document_path(slug))
        assert not isinstance(document, ContentUnavailable)

        for link in document.links:
            assert (repo_root / link).is_file(), f"{slug} links to a missing file: {link}"


def test_content_contains_no_run_specific_facts() -> None:
    """Mechanical proof of 'no run-specific interpretation' (D060-02 / D060-03)."""
    for slug in _CONTENT_SLUGS:
        document = load_content_document(content_document_path(slug))
        assert not isinstance(document, ContentUnavailable)

        for forbidden in _RUN_SPECIFIC_STRINGS:
            assert forbidden not in document.body_markdown, (
                f"{slug} contains a run-specific fact that belongs on the study page: {forbidden!r}"
            )


def test_workflow_context_does_not_show_a_synthetic_pipeline() -> None:
    """D060-02: independent processes, never 'X depends on Y' framing."""
    document = load_content_document(content_document_path("signal-predictive-workflow-context"))
    assert not isinstance(document, ContentUnavailable)

    body = document.body_markdown.lower()
    assert "independent" in body
    assert "does not depend on" in body or "does not require" in body
