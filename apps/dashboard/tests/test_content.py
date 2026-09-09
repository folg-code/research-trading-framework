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
    assert is_valid_slug("BTC Signal Quality") is False
    assert is_valid_slug("btc_signal_quality") is False
    assert is_valid_slug("") is False


def test_resolve_query_slug() -> None:
    assert resolve_query_slug({"slug": "btc-signal-quality"}, "slug") == "btc-signal-quality"
    assert resolve_query_slug({}, "slug") is None
    assert resolve_query_slug({"slug": "Not A Slug"}, "slug") is None
