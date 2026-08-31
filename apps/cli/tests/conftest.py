"""Shared fixtures for apps/cli's own test suite (D-S046-11)."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OHLCV_SAMPLE_1M = _REPO_ROOT / "tests" / "fixtures" / "market_data" / "ohlcv_sample_1m.csv"


@pytest.fixture
def ohlcv_sample_1m_path() -> Path:
    """Return the repo's committed 1m OHLCV sample fixture (read-only)."""
    assert _OHLCV_SAMPLE_1M.is_file(), f"expected fixture at {_OHLCV_SAMPLE_1M}"
    return _OHLCV_SAMPLE_1M
