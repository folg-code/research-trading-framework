"""Content-boundary error hierarchy (ADR-0034 S3).

Raised only inside :mod:`dashboard_app.content`. ``loader.py`` catches every
one of these at the boundary and converts it into an explicit
``ContentUnavailable`` value, mirroring
:mod:`dashboard_app.publication.validation`'s fail-closed pattern -- a page
never has to catch a raised exception on the render path.
"""

from __future__ import annotations


class ContentError(Exception):
    """Base for all content-boundary failures."""


class InvalidContentMetadataError(ContentError):
    """A content document's frontmatter is missing a required field or has
    an unparsable value (bad ``status``, ``updated`` date, or ``order``)."""


class DisallowedMarkdownConstructError(ContentError):
    """A content document's body uses a construct outside the restricted
    Markdown subset (ADR-0034 S3.3): raw HTML, a remote image, or a
    ``javascript:``/``data:`` link target."""
