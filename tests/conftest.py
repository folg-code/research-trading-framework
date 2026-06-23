"""Shared pytest fixtures."""

from pathlib import Path

import pytest

_MARKET_DATA_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "market_data"


@pytest.fixture
def market_data_fixtures_dir() -> Path:
    """Return the committed market data fixture directory."""
    return _MARKET_DATA_FIXTURES_DIR
