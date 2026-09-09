"""Restricted Markdown subset validation (ADR-0034 S3.3).

Deny-by-default over the whole document, not a parser: headings, paragraphs,
lists, links, emphasis, inline/fenced code, tables, and repository-local
images are accepted as-is; a raw HTML-looking construct, a remote image, or
a ``javascript:``/``data:`` link target rejects the entire document. This is
validation only -- it never rewrites or strips content, and it does not
implement a full CommonMark parser; a construct not covered by one of the
checks below is accepted, matching the small, auditable scope ADR-0034 S3.3
asks for rather than a general-purpose sanitizer.

Actual rendering (``st.markdown(document.body_markdown)``, never
``unsafe_allow_html=True``) is a caller's job (Sprint 059 T005) -- this
module only proves the text is safe to hand to that call.
"""

from __future__ import annotations

import re

from dashboard_app.content.errors import DisallowedMarkdownConstructError

#: Any HTML-looking tag start: `<div`, `<script`, `<img`, `<!--` (comments),
#: and a closing tag `</div>`. Raw HTML is not part of the allowed subset at
#: all (ADR-0034 S3.3), so no tag name allow-list is needed -- every match
#: rejects the document.
_RAW_HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z!/]")

#: Markdown image syntax: `![alt](target)`.
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

#: Markdown link syntax: `[text](target)` -- excludes the `!` prefix so an
#: image is matched by `_IMAGE_PATTERN` only, not double-counted here.
_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

_REMOTE_IMAGE_PREFIXES = ("http://", "https://", "//")
_DISALLOWED_LINK_SCHEMES = ("javascript:", "data:")


def validate_markdown_body(text: str) -> None:
    """Raise :class:`DisallowedMarkdownConstructError` on a disallowed construct.

    Returns ``None`` (does not modify ``text``) when the document is within
    the allowed subset.
    """
    if _RAW_HTML_TAG_PATTERN.search(text):
        msg = (
            "content body contains a raw HTML-looking tag, which is not part of the allowed subset"
        )
        raise DisallowedMarkdownConstructError(msg)

    for match in _IMAGE_PATTERN.finditer(text):
        target = match.group(1).strip()
        if target.lower().startswith(_REMOTE_IMAGE_PREFIXES):
            msg = (
                f"content body references a remote image, which is not repository-local: {target!r}"
            )
            raise DisallowedMarkdownConstructError(msg)

    for match in _LINK_PATTERN.finditer(text):
        target = match.group(1).strip().lower()
        if target.startswith(_DISALLOWED_LINK_SCHEMES):
            msg = f"content body uses a disallowed link scheme: {match.group(1)!r}"
            raise DisallowedMarkdownConstructError(msg)
