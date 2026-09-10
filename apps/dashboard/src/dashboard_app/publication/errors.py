"""Publication-boundary error hierarchy (ADR-0034 S1, S2).

These exceptions are raised only inside :mod:`dashboard_app.publication` and
are never expected to reach a Streamlit page render: `validation.py` catches
them at the boundary and converts every failure into an explicit
``PublicationUnavailable`` value instead. They are exported so tests can
exercise the raise path directly.
"""

from __future__ import annotations


class PublicationError(Exception):
    """Base for all publication-boundary failures."""


class InvalidProjectionSchemaError(PublicationError):
    """Raised by ``PublicProjectionBundle.from_dict`` on a missing or
    major-version-mismatched ``schema_version``, or a malformed payload
    shape."""


class UnsafePublicIdentityError(PublicationError):
    """Raised when a projected identifier could encode a path or unsafe value."""


class DuplicateArtifactIdError(PublicationError):
    """Raised when two inputs would overwrite the same projected artifact."""
