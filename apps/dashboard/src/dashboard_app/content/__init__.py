"""Version-controlled dashboard content: metadata, restricted Markdown, slug routing.

Sprint 059 T004 / ADR-0034 S3-S4. Content is reviewed like code (files in
this repository), never a CMS or database. Every document is validated on
load -- missing/invalid metadata or a disallowed Markdown construct produces
an explicit :class:`~dashboard_app.content.loader.ContentUnavailable`
result, never a raised exception on a page's render path.
"""

from __future__ import annotations

from dashboard_app.content.document import ContentDocument
from dashboard_app.content.errors import (
    ContentError,
    DisallowedMarkdownConstructError,
    InvalidContentMetadataError,
)
from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.paths import CONTENT_ROOT, content_document_path
from dashboard_app.content.routing import is_valid_slug, read_current_slug, resolve_query_slug

__all__ = [
    "CONTENT_ROOT",
    "ContentDocument",
    "ContentError",
    "ContentUnavailable",
    "DisallowedMarkdownConstructError",
    "InvalidContentMetadataError",
    "content_document_path",
    "is_valid_slug",
    "load_content_document",
    "read_current_slug",
    "resolve_query_slug",
]
