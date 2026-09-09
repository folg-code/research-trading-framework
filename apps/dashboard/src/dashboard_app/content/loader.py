"""Content document loading: frontmatter parsing + fail-closed result (ADR-0034 S3).

Metadata is a small, fixed schema (slug, title, status, updated date, order,
links) -- this module hand-parses a minimal ``key: value`` frontmatter block
rather than depending on a YAML/frontmatter library for four scalar fields
and a list:

    ---
    slug: portfolio-overview
    title: Portfolio Overview
    status: AS_BUILT
    updated: 2026-09-09
    order: 1
    links: docs/adr/ADR-0034-portfolio-publication-boundary.md,
      docs/reference/modules/DASHBOARD_APPLICATION.md
    ---

    # Markdown body...

Every failure -- a missing file, a missing/unparsable metadata field, or a
disallowed Markdown construct -- becomes an explicit ``ContentUnavailable``
result, never a raised exception reaching a caller. This mirrors
:mod:`dashboard_app.publication.validation`'s ``StudyEvidence |
PublicationUnavailable`` idiom, the same fail-closed pattern for the other
half of ADR-0034's publication boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dashboard_app.content.document import ContentDocument
from dashboard_app.content.errors import ContentError, InvalidContentMetadataError
from dashboard_app.content.markdown_safety import validate_markdown_body
from dashboard_app.publication.manifest import StudyMaturity

_FRONTMATTER_DELIMITER = "---"
_REQUIRED_FIELDS = ("slug", "title", "status", "updated", "order", "links")


@dataclass(frozen=True, slots=True)
class ContentUnavailable:
    """An explicit unavailable/invalid content state.

    ``reason`` is one of a small closed set of reason codes: ``"file_missing"``,
    ``"invalid_metadata"``, ``"disallowed_markdown"``.
    """

    reason: str
    detail: str


def load_content_document(path: Path) -> ContentDocument | ContentUnavailable:
    """Load, parse and validate one content document, failing closed on any problem."""
    if not path.is_file():
        return ContentUnavailable(reason="file_missing", detail=f"content file not found: {path}")

    raw_text = path.read_text(encoding="utf-8")

    try:
        fields, body_markdown = _parse_frontmatter(raw_text)
        document = ContentDocument(
            slug=fields["slug"],
            title=fields["title"],
            status=StudyMaturity(fields["status"]),
            updated=date.fromisoformat(fields["updated"]),
            order=int(fields["order"]),
            links=tuple(link.strip() for link in fields["links"].split(",") if link.strip()),
            body_markdown=body_markdown,
        )
    except (InvalidContentMetadataError, ValueError) as exc:
        return ContentUnavailable(reason="invalid_metadata", detail=str(exc))

    try:
        validate_markdown_body(document.body_markdown)
    except ContentError as exc:
        return ContentUnavailable(reason="disallowed_markdown", detail=str(exc))

    return document


def _parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    """Split ``raw_text`` into its frontmatter fields and Markdown body.

    Raises :class:`InvalidContentMetadataError` if the frontmatter block is
    absent/malformed or a required field is missing.
    """
    lines = raw_text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        msg = "content file does not start with a '---' frontmatter block"
        raise InvalidContentMetadataError(msg)

    try:
        closing_index = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == _FRONTMATTER_DELIMITER
        )
    except StopIteration as exc:
        msg = "content file frontmatter block is never closed with '---'"
        raise InvalidContentMetadataError(msg) from exc

    fields: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            msg = f"malformed frontmatter line (expected 'key: value'): {line!r}"
            raise InvalidContentMetadataError(msg)
        fields[key.strip()] = value.strip()

    missing = [field for field in _REQUIRED_FIELDS if field not in fields]
    if missing:
        msg = f"content frontmatter is missing required field(s): {', '.join(missing)}"
        raise InvalidContentMetadataError(msg)

    body_markdown = "\n".join(lines[closing_index + 1 :]).lstrip("\n")
    return fields, body_markdown
