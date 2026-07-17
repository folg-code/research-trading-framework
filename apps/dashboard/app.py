"""Trading research dashboard — home."""

from __future__ import annotations

import streamlit as st

from dashboard_app.ui import configure_page, render_sidebar_storage_root

configure_page(title="Trading Research Dashboard")
settings = render_sidebar_storage_root()

st.title("Trading Research Dashboard")
st.markdown(
    """
Read-only viewer for persisted research artifacts.

**MVP pages (placeholders):**

- Overview — run catalog (Wave A)
- Market / Signal Research
- Strategy Research
- Strategy Robustness

The app does **not** run backtests, research workflows, or data providers.
It only queries mounted Parquet / JSON storage via a query layer (DuckDB).
"""
)
if settings is None:
    st.warning("Configure a storage root in the sidebar or set `DASHBOARD_STORAGE_ROOT`.")
else:
    st.info(f"Active storage root: `{settings.storage_root}`")
