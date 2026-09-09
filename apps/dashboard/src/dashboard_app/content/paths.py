"""Where version-controlled dashboard content lives (ADR-0034 S3.1).

Content is repository content, not user data: it resolves relative to this
package's own location, not the mounted ``DASHBOARD_STORAGE_ROOT`` workspace
that :mod:`dashboard_app.config` and :mod:`dashboard_app.catalog.paths`
target. Sprint 059 T004 defines this location only -- populating it with
real Markdown files (the overview, workflow context, methodology) is
Sprint 059 T005's job.
"""

from __future__ import annotations

from pathlib import Path

#: apps/dashboard/content/ -- a sibling of src/, pages/ and tests/.
CONTENT_ROOT = Path(__file__).resolve().parents[3] / "content"


def content_document_path(slug: str) -> Path:
    """Return the expected file path for a content document's ``slug``.

    Does not check the file exists -- :func:`dashboard_app.content.loader.load_content_document`
    is the fail-closed entry point for that.
    """
    return CONTENT_ROOT / f"{slug}.md"
