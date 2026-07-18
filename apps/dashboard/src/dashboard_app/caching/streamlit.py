"""Cached catalog/query entry points for Streamlit pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from dashboard_app.caching.fingerprint import StorageFingerprint, compute_storage_fingerprint
from dashboard_app.catalog import RunCatalog, list_runs
from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, ChartWindow
from dashboard_app.query import DashboardQueryService, OhlcvWindowResult


def storage_fingerprint(storage_root: Path) -> StorageFingerprint:
    """Compute (and Streamlit-cache) a storage fingerprint for cache keys."""
    return _cached_fingerprint(str(storage_root.expanduser().resolve()))


@st.cache_data(show_spinner=False)
def _cached_fingerprint(storage_root: str) -> StorageFingerprint:
    return compute_storage_fingerprint(Path(storage_root))


@st.cache_data(show_spinner=False)
def cached_list_runs(storage_root: str, fingerprint_token: str) -> RunCatalog:
    """List runs with Streamlit cache keyed by storage fingerprint."""
    del fingerprint_token  # included so Streamlit invalidates when storage changes
    return list_runs(Path(storage_root))


@st.cache_data(show_spinner=False)
def cached_ohlcv_window(
    storage_root: str,
    fingerprint_token: str,
    dataset_ref: str,
    start_at: str,
    end_at: str,
    timeframe: str,
    max_bars: int | None,
) -> OhlcvWindowResult:
    """Windowed OHLCV read with Streamlit cache keyed by fingerprint + window."""
    del fingerprint_token
    from datetime import datetime

    service = DashboardQueryService(Path(storage_root))
    window = ChartWindow(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        start_at_utc=datetime.fromisoformat(start_at),
        end_at_utc=datetime.fromisoformat(end_at),
        timeframe=timeframe,
        max_bars=max_bars,
    )
    return service.read_ohlcv_window(dataset_ref=dataset_ref, window=window)
