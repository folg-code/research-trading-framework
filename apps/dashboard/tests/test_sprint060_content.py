"""Tests for Sprint 060 T002's workflow-context and methodology content.

D060-02 requires Signal Research and Predictive Research to be presented
as separate processes, never a synthetic end-to-end pipeline; the
methodology page must be living, run-agnostic content with no
run-specific interpretation. These tests prove both documents load
cleanly and mechanically confirm no run-specific fact leaked in.
"""

from __future__ import annotations

import re
from pathlib import Path

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path
from dashboard_app.publication.manifest import StudyMaturity

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]

#: Facts specific to the real BTC Signal Quality study run -- none of
#: these belong in general workflow/methodology content (that is T003's
#: study page, sourced from the publication/ projection). Named literals
#: for the facts a careless edit is most likely to reach for (a persisted
#: verdict value, a fired rule id); the two regexes below generalize
#: beyond this fixed list to any id/fingerprint- or metric-value-shaped
#: token, so a *different* run-specific fact from a future edit is still
#: caught -- a narrow literal-only list was flagged as the exact weakness
#: an earlier content review (Sprint 059 T005) found in a similar test.
_RUN_SPECIFIC_STRINGS = (
    "2ef6426b3cc06463",  # the run id
    "437f6b7f9240208f",  # the dataset id
    "8d050f623a034a58",  # baseline Strategy Research run id
    "4dbf98822e6ae591",  # scored Strategy Research run id
    "PASS",
    "WEAK_PASS",
    "INCONCLUSIVE",
    "FAIL",
    "REJECTED_OVERFIT",
    "REJECTED_LEAKAGE_RISK",
    "REJECTED_LOW_SAMPLE",
    "REJECTED_CONCENTRATION",  # the 8-value verdict vocabulary -- a value name
    # itself is run-specific evidence; the general vocabulary is discussed
    # only in prose (e.g. "overfitting"), never as the literal enum string.
)

#: A 16+ hex-digit token matches this study's run id, dataset id, and
#: promoted-artifact fingerprint shape generically -- catches a *different*
#: id leaking in, not just the four named above.
_ID_SHAPED_TOKEN = re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE)

#: A decimal value with 3+ digits after the point matches this study's
#: metric-precision values (e.g. a pooled ROC AUC) without flagging a
#: plain date or a schema version number.
_PRECISE_DECIMAL = re.compile(r"\d+\.\d{3,}")

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

        id_match = _ID_SHAPED_TOKEN.search(document.body_markdown)
        assert id_match is None, f"{slug} contains an id/fingerprint-shaped token: {id_match!r}"

        decimal_match = _PRECISE_DECIMAL.search(document.body_markdown)
        assert decimal_match is None, (
            f"{slug} contains a metric-precision decimal value: {decimal_match!r}"
        )


def test_workflow_context_does_not_show_a_synthetic_pipeline() -> None:
    """D060-02: independent processes, never 'X depends on Y' framing."""
    document = load_content_document(content_document_path("signal-predictive-workflow-context"))
    assert not isinstance(document, ContentUnavailable)

    body = document.body_markdown.lower()
    assert "independent" in body
    assert "does not depend on" in body or "does not require" in body
