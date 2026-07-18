"""Shared Streamlit page chrome and storage-root controls."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from dashboard_app.config import (
    DashboardSettings,
    load_settings,
    resolve_status_url,
    storage_root_status,
)

_ENV_STORAGE_ROOT = "DASHBOARD_STORAGE_ROOT"
_ENV_GITHUB_URL = "DASHBOARD_GITHUB_URL"
_DEFAULT_GITHUB_URL = "https://github.com/folg-code/research-trading-framework"
_PROJECT_NAME = "Trading Research Framework"


def configure_page(*, title: str, icon: str = "📊") -> None:
    """Apply common Streamlit page configuration."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")


def env_storage_configured() -> bool:
    """Return True when ``DASHBOARD_STORAGE_ROOT`` is set in the environment."""
    raw = os.environ.get(_ENV_STORAGE_ROOT)
    return raw is not None and bool(raw.strip())


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


def render_app_chrome() -> DashboardSettings | None:
    """Render public sidebar chrome and return settings when resolvable.

    When ``DASHBOARD_STORAGE_ROOT`` is set (typical VPS Compose), storage and
    status URL are not editable. Diagnostics stay collapsed.
    """
    st.sidebar.markdown(f"**{_PROJECT_NAME}**")
    github_url = os.environ.get(_ENV_GITHUB_URL, _DEFAULT_GITHUB_URL).strip()
    if github_url:
        st.sidebar.markdown(f"[GitHub]({github_url})")

    locked = env_storage_configured()
    with st.sidebar.expander("System diagnostics", expanded=False):
        if locked:
            st.caption("Storage and status URL are fixed by deployment environment.")
            try:
                settings = load_settings(
                    status_url=st.session_state.get("status_url") or None,
                )
            except ValueError as exc:
                st.error(str(exc))
                return None
            st.session_state["storage_root"] = str(settings.storage_root)
            st.session_state["status_url"] = settings.status_url or ""
            _render_diagnostics_status(settings, editable=False)
            return settings

        default = st.session_state.get("storage_root", "")
        raw = st.text_input(
            "Workspace root (contains market_data/ and research/)",
            value=str(default),
            help="Same layout as trading-framework user_data/. "
            "Can also be set via DASHBOARD_STORAGE_ROOT.",
            key="diagnostics_storage_root",
        )
        status_default = st.session_state.get("status_url", "") or (resolve_status_url() or "")
        status_raw = st.text_input(
            "Live paper status URL (optional)",
            value=str(status_default),
            help="Read-only GET endpoint (DASHBOARD_STATUS_URL). Never used to trade.",
            key="diagnostics_status_url",
        )
        try:
            if raw.strip():
                st.session_state["storage_root"] = raw.strip()
                settings = load_settings(
                    storage_root=Path(raw.strip()),
                    status_url=status_raw,
                )
            else:
                settings = load_settings(status_url=status_raw)
        except ValueError as exc:
            st.error(str(exc))
            return None

        st.session_state["status_url"] = status_raw.strip()
        _render_diagnostics_status(settings, editable=True)
        return settings


def render_sidebar_storage_root() -> DashboardSettings | None:
    """Backward-compatible alias for :func:`render_app_chrome`."""
    return render_app_chrome()


def _render_diagnostics_status(settings: DashboardSettings, *, editable: bool) -> None:
    status = storage_root_status(settings)
    st.write(f"`{settings.storage_root}`")
    st.write(
        {
            "root": "✅" if status["storage_root_exists"] else "❌",
            "market_data": "✅" if status["market_data_exists"] else "❌",
            "research": "✅" if status["research_exists"] else "❌",
            "status_url": ("✅ configured" if settings.status_url else "—"),
            "status_host": mask_status_url(settings.status_url),
            "editable": editable,
        }
    )
