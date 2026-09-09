"""Tests for the content loader, metadata validation and slug routing.

Sprint 059 T004 / ADR-0034 S3-S4. Fixtures are written inline via ``tmp_path``,
matching the flat, no-``conftest.py`` convention already used by
``test_config.py`` and ``test_publication.py``.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from dashboard_app.content.loader import ContentUnavailable, load_content_document
from dashboard_app.content.routing import is_valid_slug, resolve_query_slug
from dashboard_app.publication.manifest import StudyMaturity

_VALID_FRONTMATTER = """\
---
slug: portfolio-overview
title: Portfolio Overview
status: AS_BUILT
updated: 2026-09-09
order: 1
links: docs/adr/ADR-0034.md, docs/reference/modules/DASHBOARD_APPLICATION.md
---
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_load_content_document_well_formed(tmp_path: Path) -> None:
    body = (
        "# Portfolio Overview\n\nSome *safe* explanatory text with a "
        "[link](docs/adr/ADR-0034.md).\n"
    )
    path = _write(tmp_path / "portfolio-overview.md", _VALID_FRONTMATTER + "\n" + body)

    document = load_content_document(path)

    assert not isinstance(document, ContentUnavailable)
    assert document.slug == "portfolio-overview"
    assert document.title == "Portfolio Overview"
    assert document.status == StudyMaturity.AS_BUILT
    assert document.updated == date(2026, 9, 9)
    assert document.order == 1
    assert document.links == (
        "docs/adr/ADR-0034.md",
        "docs/reference/modules/DASHBOARD_APPLICATION.md",
    )
    assert "Portfolio Overview" in document.body_markdown


def test_load_content_document_missing_file_returns_unavailable(tmp_path: Path) -> None:
    result = load_content_document(tmp_path / "does-not-exist.md")

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "file_missing"


def test_load_content_document_unreadable_encoding_returns_unavailable(tmp_path: Path) -> None:
    """A non-UTF-8 file must fail closed, not raise UnicodeDecodeError."""
    path = tmp_path / "bad-encoding.md"
    path.write_bytes(b"\xff\xfe not valid utf-8")

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "file_unreadable"


def test_load_content_document_missing_frontmatter_start_returns_unavailable(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "no-frontmatter.md", "# Just a heading, no frontmatter block\n")

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_unclosed_frontmatter_returns_unavailable(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "unclosed.md", "---\nslug: x\ntitle: X\n\nBody without a closing ---\n"
    )

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_malformed_frontmatter_line_returns_unavailable(
    tmp_path: Path,
) -> None:
    text = _VALID_FRONTMATTER.replace("order: 1", "order 1") + "\nBody.\n"
    path = _write(tmp_path / "malformed-line.md", text)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_invalid_status_returns_unavailable(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("status: AS_BUILT", "status: SHIPPED") + "\nBody.\n"
    path = _write(tmp_path / "bad-status.md", text)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_invalid_date_returns_unavailable(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("updated: 2026-09-09", "updated: not-a-date") + "\nBody.\n"
    path = _write(tmp_path / "bad-date.md", text)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_invalid_order_returns_unavailable(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("order: 1", "order: first") + "\nBody.\n"
    path = _write(tmp_path / "bad-order.md", text)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_missing_required_field_returns_unavailable(tmp_path: Path) -> None:
    text = _VALID_FRONTMATTER.replace("title: Portfolio Overview\n", "") + "\nBody.\n"
    path = _write(tmp_path / "missing-title.md", text)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "invalid_metadata"


def test_load_content_document_rejects_raw_html(tmp_path: Path) -> None:
    body = "# Heading\n\n<script>alert('x')</script>\n"
    path = _write(tmp_path / "raw-html.md", _VALID_FRONTMATTER + "\n" + body)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "disallowed_markdown"


def test_load_content_document_rejects_remote_image(tmp_path: Path) -> None:
    body = "# Heading\n\n![chart](https://example.com/chart.png)\n"
    path = _write(tmp_path / "remote-image.md", _VALID_FRONTMATTER + "\n" + body)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "disallowed_markdown"


def test_load_content_document_rejects_disallowed_link_scheme(tmp_path: Path) -> None:
    body = "# Heading\n\n[click here](javascript:alert(1))\n"
    path = _write(tmp_path / "js-link.md", _VALID_FRONTMATTER + "\n" + body)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "disallowed_markdown"


def test_load_content_document_rejects_reference_style_remote_image(tmp_path: Path) -> None:
    body = "# Heading\n\n![chart][1]\n\n[1]: https://evil.example.com/x.png\n"
    path = _write(tmp_path / "reference-image.md", _VALID_FRONTMATTER + "\n" + body)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "disallowed_markdown"


def test_load_content_document_rejects_reference_style_disallowed_scheme(tmp_path: Path) -> None:
    body = "# Heading\n\n[click here][1]\n\n[1]: javascript:alert(1)\n"
    path = _write(tmp_path / "reference-link.md", _VALID_FRONTMATTER + "\n" + body)

    result = load_content_document(path)

    assert isinstance(result, ContentUnavailable)
    assert result.reason == "disallowed_markdown"


def test_load_content_document_accepts_reference_style_safe_link(tmp_path: Path) -> None:
    body = "# Heading\n\n[docs][1]\n\n[1]: https://example.com/docs\n"
    path = _write(tmp_path / "reference-safe.md", _VALID_FRONTMATTER + "\n" + body)

    document = load_content_document(path)

    assert not isinstance(document, ContentUnavailable)


def test_load_content_document_fenced_code_with_angle_brackets_is_accepted(
    tmp_path: Path,
) -> None:
    """Regression: a `<` inside fenced code (e.g. generics) must not be
    treated as raw HTML -- ADR-0034 S3.3 explicitly allows fenced code."""
    body = "# Heading\n\n```java\nList<String> xs = new ArrayList<String>();\n```\n"
    path = _write(tmp_path / "generics.md", _VALID_FRONTMATTER + "\n" + body)

    document = load_content_document(path)

    assert not isinstance(document, ContentUnavailable)


def test_load_content_document_accepts_repo_local_image(tmp_path: Path) -> None:
    body = "# Heading\n\n![chart](../images/chart.png)\n"
    path = _write(tmp_path / "local-image.md", _VALID_FRONTMATTER + "\n" + body)

    document = load_content_document(path)

    assert not isinstance(document, ContentUnavailable)


def test_load_content_document_accepts_the_full_allowed_subset(tmp_path: Path) -> None:
    body = (
        "# Heading\n\n"
        "## Subheading\n\n"
        "A paragraph with **bold**, *italic*, and `inline code`.\n\n"
        "- one\n- two\n\n"
        "```python\nx = 1\n```\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "A [relative link](docs/reference/README.md) and an "
        "[https link](https://example.com/docs).\n"
    )
    path = _write(tmp_path / "full-subset.md", _VALID_FRONTMATTER + "\n" + body)

    document = load_content_document(path)

    assert not isinstance(document, ContentUnavailable)


def test_is_valid_slug() -> None:
    assert is_valid_slug("btc-signal-quality") is True
    assert is_valid_slug("a") is True
    assert is_valid_slug("BTC Signal Quality") is False
    assert is_valid_slug("btc_signal_quality") is False
    assert is_valid_slug("") is False
    assert is_valid_slug("a--b") is False
    assert is_valid_slug("a-") is False
    assert is_valid_slug("-a") is False


def test_resolve_query_slug() -> None:
    assert resolve_query_slug({"slug": "btc-signal-quality"}, "slug") == "btc-signal-quality"
    assert resolve_query_slug({}, "slug") is None
    assert resolve_query_slug({"slug": "Not A Slug"}, "slug") is None
