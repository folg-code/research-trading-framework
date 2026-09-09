"""Restricted Markdown subset validation (ADR-0034 S3.3).

Deny-by-default over the whole document, not a parser: headings, paragraphs,
lists, links, emphasis, inline/fenced code, tables, and repository-local
images are accepted as-is; a raw HTML-looking construct, a remote image, or
a ``javascript:``/``data:`` link target rejects the entire document. This is
validation only -- it never rewrites or strips content, and it does not
implement a full CommonMark parser; a construct not covered by one of the
checks below is accepted, matching the small, auditable scope ADR-0034 S3.3
asks for rather than a general-purpose sanitizer.

Both inline (``[text](target)`` / ``![alt](target)``) and CommonMark
reference-style (``[text][label]`` / ``![alt][label]`` with a separate
``[label]: target`` definition line) link and image forms are checked --
reference style is a legitimate, unlisted construct that would otherwise
carry an unchecked target past every scheme/remote-image check below.

Actual rendering (``st.markdown(document.body_markdown)``, never
``unsafe_allow_html=True``) is a caller's job (Sprint 059 T005) -- this
module only proves the text is safe to hand to that call.
"""

from __future__ import annotations

import re

from dashboard_app.content.errors import DisallowedMarkdownConstructError

#: A fenced code block's content is opaque text, never interpreted as
#: Markdown or HTML -- ADR-0034 S3.3 explicitly allows fenced code, so a
#: `<` inside one (e.g. a generic type like `List<String>`) must not trip
#: the raw-HTML check below. Stripped before that check only; link/image
#: patterns are harmless against code-block content in practice and are
#: left running against the full text.
_FENCED_CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)

#: Any HTML-looking tag start: `<div`, `<script`, `<img`, `<!--` (comments),
#: and a closing tag `</div>`. Raw HTML is not part of the allowed subset at
#: all (ADR-0034 S3.3), so no tag name allow-list is needed -- every match
#: rejects the document.
_RAW_HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z!/]")

#: Inline Markdown image syntax: `![alt](target)`.
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

#: Inline Markdown link syntax: `[text](target)` -- excludes the `!` prefix
#: so an image is matched by `_IMAGE_PATTERN` only, not double-counted here.
_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

#: Reference-style image usage: `![alt][label]` (a bare `![alt][]` collapsed
#: reference uses `alt` itself as the label -- handled in code below).
_REFERENCE_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\[([^\]]*)\]")

#: A reference definition line: `[label]: target` (CommonMark allows up to
#: three leading spaces). Matched on every line regardless of whether a
#: usage pattern above also matched it -- every defined target's scheme is
#: checked unconditionally (see below), since the same definition could be
#: consumed by a link OR an image usage.
_REFERENCE_DEFINITION_PATTERN = re.compile(r"^[ ]{0,3}\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)

_REMOTE_IMAGE_PREFIXES = ("http://", "https://", "//")
_DISALLOWED_LINK_SCHEMES = ("javascript:", "data:")


def validate_markdown_body(text: str) -> None:
    """Raise :class:`DisallowedMarkdownConstructError` on a disallowed construct.

    Returns ``None`` (does not modify ``text``) when the document is within
    the allowed subset.
    """
    without_code_blocks = _FENCED_CODE_BLOCK_PATTERN.sub("", text)
    if _RAW_HTML_TAG_PATTERN.search(without_code_blocks):
        msg = (
            "content body contains a raw HTML-looking tag, which is not part of the allowed subset"
        )
        raise DisallowedMarkdownConstructError(msg)

    for match in _IMAGE_PATTERN.finditer(text):
        _reject_if_remote_image(match.group(1))

    for match in _LINK_PATTERN.finditer(text):
        _reject_if_disallowed_scheme(match.group(1))

    reference_definitions = {
        label.strip().lower(): target
        for label, target in _REFERENCE_DEFINITION_PATTERN.findall(text)
    }

    # Every defined reference target's scheme is checked regardless of how
    # (or whether) it is used -- a `javascript:`/`data:` target is rejected
    # even if only a link usage regex would otherwise have matched it,
    # closing the gap a link-vs-image usage classifier could otherwise miss.
    for target in reference_definitions.values():
        _reject_if_disallowed_scheme(target)

    for alt, label in _REFERENCE_IMAGE_PATTERN.findall(text):
        resolved_label = (label or alt).strip().lower()
        target = reference_definitions.get(resolved_label)
        if target is not None:
            _reject_if_remote_image(target)


def _reject_if_remote_image(target: str) -> None:
    stripped = target.strip()
    if stripped.lower().startswith(_REMOTE_IMAGE_PREFIXES):
        msg = f"content body references a remote image, which is not repository-local: {stripped!r}"
        raise DisallowedMarkdownConstructError(msg)


def _reject_if_disallowed_scheme(target: str) -> None:
    stripped = target.strip()
    if stripped.lower().startswith(_DISALLOWED_LINK_SCHEMES):
        msg = f"content body uses a disallowed link scheme: {stripped!r}"
        raise DisallowedMarkdownConstructError(msg)
