"""Shared committed fixture paths for spike scripts."""

from pathlib import Path

OHLCV_SAMPLE_1M_FILENAME = "ohlcv_sample_1m.csv"
OHLCV_SAMPLE_1M = (
    Path(__file__).resolve().parents[1] / "fixtures" / "market_data" / OHLCV_SAMPLE_1M_FILENAME
)
