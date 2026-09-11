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
STUDY_PAGE = "pages/9_Signal_Quality_Study.py"


def render_static_content_page(
    slug: str,
    *,
    architecture_diagram: str | None = None,
) -> None:
    """Render one stable, version-controlled portfolio content page."""
    document = load_content_document(content_document_path(slug))
    if isinstance(document, ContentUnavailable):
        st.warning(f"Content unavailable ({document.reason}): {document.detail}")
        return

    st.title(document.title)
    status = document.status.value.replace("_", " ")
    st.caption(f"{status} · Updated {document.updated.isoformat()}")
    if architecture_diagram is not None:
        st.subheader("System map")
        st.caption(
            "Arrows show data or contract consumption. Market Data stops at DatasetRef; "
            "each workflow owns the evidence it produces."
        )
        st.mermaid_chart(architecture_diagram)
    st.markdown(document.body_markdown)


def render_workflow_publication(slug: str, *, evidence_page: str, evidence_label: str) -> None:
    """Render workflow methodology first, then offer its technical evidence view."""
    render_static_content_page(slug)
    st.divider()
    st.subheader("Explore Evidence")
    st.caption(
        "The technical view below reads persisted artifacts. It is evidence for this "
        "workflow, not a substitute for its methodology and architecture."
    )
    st.page_link(evidence_page, label=evidence_label)


def render_future_direction_entries() -> None:
    """Link the Future Direction index to exactly its two approved ideas."""
    columns = st.columns(2)
    entries = (
        (
            "AI Research Infrastructure",
            "pages/13_AI_Research_Infrastructure.py",
            "A proposed AI control plane over deterministic framework operations.",
        ),
        (
            "Research Application",
            "pages/14_Research_Application.py",
            "A draft local-first interface for existing framework workflows.",
        ),
    )
    for (title, page_path, description), column in zip(entries, columns, strict=True):
        with column:
            st.subheader(title)
            st.badge("FUTURE IDEAS", color="violet")
            st.write(description)
            st.page_link(page_path, label=f"Explore {title}")


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
        forward_label="Open the Signal Quality study",
    )


def render_portfolio_evidence_entry_point() -> None:
    """Render the overview's one-action entry point into the evidence path."""
    st.subheader("Signal Quality Portfolio Evidence")
    st.caption(
        "A worked example connecting Signal Research, Predictive Research and "
        "Strategy Research through one persisted, allowlisted study."
    )
    st.page_link(WORKFLOW_CONTEXT_PAGE, label="Start the Signal Quality workflow context")
