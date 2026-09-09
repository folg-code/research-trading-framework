"""Stable-slug routing contract (ADR-0034 S4).

A slug is a public identifier for a content concept (an overview, a
workflow, a study). Query parameters may carry a study or evidence target
slug so a page reopens correctly in a new browser session; nothing here
writes to ``st.session_state`` or otherwise persists a transient selection
(ADR-0034 S4.3) -- a slug is read fresh from the current URL on every run.

This module deliberately does not enumerate concrete routes (which slug
belongs to which page): no portfolio pages exist yet. It provides the slug
format contract and the query-parameter read path a future page (Sprint 059
T005+) uses.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import streamlit as st

#: Lowercase letters, digits and hyphens only -- e.g. "btc-signal-quality".
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def is_valid_slug(slug: str) -> bool:
    """Return whether ``slug`` matches the stable-slug format (ADR-0034 S4.1)."""
    return bool(_SLUG_PATTERN.match(slug))


def resolve_query_slug(query_params: Mapping[str, str], param_name: str = "slug") -> str | None:
    """Return a validly-formatted slug from ``query_params``, or ``None``.

    Pure and fully unit-testable without a Streamlit runtime. Fails closed:
    a present-but-malformed value returns ``None`` rather than passing a bad
    slug through to a caller.
    """
    value = query_params.get(param_name)
    if value is None or not is_valid_slug(value):
        return None
    return value


def read_current_slug(param_name: str = "slug") -> str | None:
    """Read the current browser URL's slug query parameter, if any.

    Thin wrapper over ``st.query_params`` (a Streamlit-runtime-only API);
    all format validation lives in :func:`resolve_query_slug`, which this
    delegates to.
    """
    return resolve_query_slug(dict(st.query_params), param_name)
