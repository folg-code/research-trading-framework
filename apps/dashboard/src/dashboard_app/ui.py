"""Shared Streamlit page chrome and storage-root controls."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard_app.config import (
    DashboardSettings,
    load_settings,
    resolve_status_url,
    storage_root_status,
)


def configure_page(*, title: str, icon: str = "📊") -> None:
    """Apply common Streamlit page configuration."""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")


def render_sidebar_storage_root() -> DashboardSettings | None:
    """Render storage-root input and return settings when resolvable."""
    st.sidebar.header("Storage")
    default = st.session_state.get("storage_root", "")
    raw = st.sidebar.text_input(
        "Workspace root (contains market_data/ and research/)",
        value=str(default),
        help="Same layout as trading-framework user_data/. "
        "Can also be set via DASHBOARD_STORAGE_ROOT.",
    )
    status_default = st.session_state.get("status_url", "") or (resolve_status_url() or "")
    status_raw = st.sidebar.text_input(
        "Live paper status URL (optional)",
        value=str(status_default),
        help="Read-only GET endpoint (DASHBOARD_STATUS_URL). Never used to trade.",
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
        st.sidebar.error(str(exc))
        return None

    st.session_state["status_url"] = status_raw.strip()
    status = storage_root_status(settings)
    st.sidebar.write(f"`{settings.storage_root}`")
    st.sidebar.write(
        {
            "root": "✅" if status["storage_root_exists"] else "❌",
            "market_data": "✅" if status["market_data_exists"] else "❌",
            "research": "✅" if status["research_exists"] else "❌",
            "status_url": "✅" if settings.status_url else "—",
        }
    )
    return settings
