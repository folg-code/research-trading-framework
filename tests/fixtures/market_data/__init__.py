"""Committed market-data CSV fixtures for tests and spikes."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent

OHLCV_SAMPLE_1M_FILENAME = "ohlcv_sample_1m.csv"
OHLCV_SAMPLE_1M = FIXTURES_DIR / OHLCV_SAMPLE_1M_FILENAME

# First data row in ``ohlcv_sample_1m.csv`` (2018-12-31 00:00 UTC).
OHLCV_SAMPLE_1M_FIRST_CLOSE = "1279.675"
OHLCV_SAMPLE_1M_ROW_COUNT = 1321

__all__ = [
    "FIXTURES_DIR",
    "OHLCV_SAMPLE_1M",
    "OHLCV_SAMPLE_1M_FILENAME",
    "OHLCV_SAMPLE_1M_FIRST_CLOSE",
    "OHLCV_SAMPLE_1M_ROW_COUNT",
]
