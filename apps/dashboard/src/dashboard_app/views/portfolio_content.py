"""Signal Quality portfolio evidence path: workflow context -> methodology
-> study (Sprint 060 T004; ADR-0034 S4 stable routes; PRD's "accessible
workflow context -> current methodology -> Signal Quality study ->
simplified result -> Explore Evidence" pattern).

Each render function here loads one version-controlled content document
(``dashboard_app.content``) and adds a single one-action link forward to
the next page in the path -- it never duplicates that next page's content.
"""

from __future__ import annotations

import streamlit as st

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import content_document_path

#: The evidence path's page routes, in order (ADR-0034 S4.1: stable
#: Streamlit page routes). Kept as one tuple so the overview entry point,
#: the workflow-context page and the methodology page all point at the
#: same page files rather than each hard-coding its own copy.
WORKFLOW_CONTEXT_PAGE = "pages/7_Signal_Quality_Workflow.py"
METHODOLOGY_PAGE = "pages/8_Signal_Quality_Methodology.py"
STUDY_PAGE = "pages/9_BTC_Signal_Quality_Study.py"


def _render_content_document_with_forward_link(
    slug: str, *, forward_page: str, forward_label: str
) -> None:
    document = load_content_document(content_document_path(slug))
    if isinstance(document, ContentUnavailable):
        st.warning(f"Content unavailable ({document.reason}): {document.detail}")
        return

    st.title(document.title)
    st.markdown(document.body_markdown)
    st.divider()
    st.page_link(forward_page, label=forward_label)


def render_signal_predictive_workflow_context() -> None:
    """Render the Signal/Predictive workflow-context content document."""
    _render_content_document_with_forward_link(
        "signal-predictive-workflow-context",
        forward_page=METHODOLOGY_PAGE,
        forward_label="Open Signal Quality Methodology",
    )


def render_signal_quality_methodology() -> None:
    """Render the Signal Quality methodology content document."""
    _render_content_document_with_forward_link(
        "signal-quality-methodology",
        forward_page=STUDY_PAGE,
        forward_label="Open the BTC Signal Quality study",
    )


def render_portfolio_evidence_entry_point() -> None:
    """Render the overview's one-action entry point into the evidence path."""
    st.subheader("Signal Quality Portfolio Evidence")
    st.caption(
        "A worked example connecting Signal Research, Predictive Research and "
        "Strategy Research through one persisted, allowlisted study."
    )
    st.page_link(WORKFLOW_CONTEXT_PAGE, label="Start the Signal Quality workflow context")
