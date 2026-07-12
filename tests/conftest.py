"""Shared pytest fixtures."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.fixtures.market_data import OHLCV_SAMPLE_1M
from trading_framework.market_analysis.assembly.frame import AnalysisFrame

_MARKET_DATA_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "market_data"


@pytest.fixture
def market_data_fixtures_dir() -> Path:
    """Return the committed market data fixture directory."""
    return _MARKET_DATA_FIXTURES_DIR


@pytest.fixture
def ohlcv_sample_1m_path() -> Path:
    """Return the canonical committed 1m OHLCV sample fixture."""
    return OHLCV_SAMPLE_1M


@pytest.fixture
def build_test_frame() -> Callable[..., AnalysisFrame]:
    """Build a minimal aligned AnalysisFrame for model evaluation tests."""

    def _build(
        *,
        columns: dict[str, tuple[float, ...]],
        start: datetime | None = None,
        step: timedelta | None = None,
    ) -> AnalysisFrame:
        base = start or datetime(2024, 6, 3, 14, 30, tzinfo=UTC)
        delta = step or timedelta(minutes=1)
        length = len(next(iter(columns.values())))
        timestamps = tuple(base + delta * index for index in range(length))
        if not all(len(values) == length for values in columns.values()):
            msg = "all frame columns must share the same length"
            raise ValueError(msg)
        return AnalysisFrame(
            timestamps=timestamps,
            columns=columns,
            column_lineage={},
        )

    return _build
