"""One version-controlled content document's parsed representation (ADR-0034 S3.2).

``status`` reuses :class:`dashboard_app.publication.manifest.StudyMaturity`
rather than a second enum -- ADR-0034 S3.2 names the exact same four-value
vocabulary (``AS_BUILT`` / ``IN_DEVELOPMENT`` / ``FUTURE_IDEAS`` /
``ARCHIVED``) already declared there for study maturity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dashboard_app.publication.manifest import StudyMaturity


@dataclass(frozen=True, slots=True)
class ContentDocument:
    """One loaded, metadata-validated, Markdown-safety-checked content document.

    ``body_markdown`` has already passed
    :func:`dashboard_app.content.markdown_safety.validate_markdown_body` by
    the time a :class:`ContentDocument` exists -- a caller may render it with
    ``st.markdown(document.body_markdown)`` (never ``unsafe_allow_html=True``)
    without a further safety check.
    """

    slug: str
    title: str
    status: StudyMaturity
    updated: date
    order: int
    links: tuple[str, ...]
    body_markdown: str
