"""Conservative public identifiers shared by projection producers and readers."""

from __future__ import annotations

import re

_SAFE_ARTIFACT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,191}$")
_SAFE_IDENTITY_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@|+\-]{0,255}$")


def is_safe_artifact_id(value: str) -> bool:
    """Return whether ``value`` is a projection-local, non-path identifier."""
    return _SAFE_ARTIFACT_ID.fullmatch(value) is not None


def is_safe_identity_value(value: str) -> bool:
    """Return whether a persisted identity is conservative and non-path-like."""
    return _SAFE_IDENTITY_VALUE.fullmatch(value) is not None


def is_safe_public_text(value: str) -> bool:
    """Reject empty, control-character and path-like display strings."""
    return (
        bool(value.strip())
        and not any(ord(char) < 32 for char in value)
        and not any(separator in value for separator in ("/", "\\"))
    )
