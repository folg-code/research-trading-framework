"""Shared Streamlit chrome for the public read-only dashboard."""

from __future__ import annotations

import os

import streamlit as st

from dashboard_app.config import resolve_status_url
from dashboard_app.publication.paths import projection_bundle_path
from dashboard_app.publication.validation import (
    PublicationUnavailable,
    load_projection_bundle_from_path,
)

_ENV_GITHUB_URL = "DASHBOARD_GITHUB_URL"
_DEFAULT_GITHUB_URL = "https://github.com/folg-code/research-trading-framework"
_PROJECT_NAME = "Trading Research Framework"

_ENV_AUTHOR_EMAIL = "DASHBOARD_AUTHOR_EMAIL"
_ENV_AUTHOR_LINKEDIN_URL = "DASHBOARD_AUTHOR_LINKEDIN_URL"
_DEFAULT_AUTHOR_NAME = "Filip Folga"
_DEFAULT_AUTHOR_EMAIL = "filip1folga@gmail.com"
_DEFAULT_AUTHOR_LINKEDIN_URL = "https://www.linkedin.com/in/filip-folga/"

#: `st.page_link`'s visible label renders in a `<p>` with an explicit text
#: color rather than inheriting the anchor's link color, so the `theme.
#: linkColor` config (.streamlit/config.toml) alone does not reach it. Force
#: it to the same bright yellow so subpage links read as links everywhere,
#: not just in Markdown-rendered prose.
_PAGE_LINK_COLOR_CSS = """
<style>
[data-testid="stPageLink"] p {
    color: #FFEB3B !important;
}
</style>
"""


def configure_page(*, title: str, icon: str = "📊") -> None:
    """Apply common Streamlit page configuration."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.html(_PAGE_LINK_COLOR_CSS)


def mask_status_url(url: str | None) -> str:
    """Return a shortened status URL for public diagnostics."""
    if url is None or not url.strip():
        return "—"
    text = url.strip()
    if "://" not in text:
        return text[:24] + ("…" if len(text) > 24 else "")
    scheme, rest = text.split("://", 1)
    host = rest.split("/", 1)[0]
    return f"{scheme}://{host}/…"


def render_app_chrome() -> None:
    """Render public navigation chrome without exposing workspace controls."""
    st.sidebar.markdown(f"**{_PROJECT_NAME}**")
    github_url = os.environ.get(_ENV_GITHUB_URL, _DEFAULT_GITHUB_URL).strip()
    if github_url:
        st.sidebar.markdown(f"[GitHub]({github_url})")

    st.sidebar.caption(f"Built by {_DEFAULT_AUTHOR_NAME}")
    linkedin_url = os.environ.get(_ENV_AUTHOR_LINKEDIN_URL, _DEFAULT_AUTHOR_LINKEDIN_URL).strip()
    if linkedin_url:
        st.sidebar.markdown(f"[LinkedIn]({linkedin_url})")
    author_email = os.environ.get(_ENV_AUTHOR_EMAIL, _DEFAULT_AUTHOR_EMAIL).strip()
    if author_email:
        st.sidebar.markdown(f"[Email](mailto:{author_email})")

    with st.sidebar.expander("System diagnostics", expanded=False):
        bundle = load_projection_bundle_from_path(projection_bundle_path())
        if isinstance(bundle, PublicationUnavailable):
            st.write({"public evidence": f"unavailable ({bundle.reason})"})
        else:
            st.write(
                {
                    "public evidence": "✅ validated",
                    "schema": bundle.schema_version,
                    "artifacts": len(bundle.artifacts),
                }
            )
        status_url = resolve_status_url()
        st.write(
            {
                "live paper status": "✅ configured" if status_url else "—",
                "status host": mask_status_url(status_url),
            }
        )
