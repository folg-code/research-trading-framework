"""Parquet-backed dataset repository."""

from collections.abc import Sequence
from pathlib import Path

from trading_framework.infrastructure.storage.parquet.writer import ParquetBarWriter
from trading_framework.infrastructure.storage.paths import dataset_bars_path
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import HistoricalBarQuery


class ParquetDatasetRepository:
    """Persist and query OHLCV bars stored as Parquet files."""

    def __init__(
        self,
        root: Path,
        writer: ParquetBarWriter | None = None,
    ) -> None:
        self._root = root
        self._writer = writer or ParquetBarWriter()

    def write_bars(self, dataset_ref: DatasetRef, bars: Sequence[MarketBar]) -> None:
        """Persist bars for the given dataset version."""
        path = dataset_bars_path(self._root, dataset_ref)
        self._writer.write(path, bars)

    def query_bars(self, query: HistoricalBarQuery) -> Sequence[MarketBar]:
        """Return bars in time order for the requested dataset range."""
        path = dataset_bars_path(self._root, query.dataset_ref)
        if not path.exists():
            return []
        bars = self._writer.read(path)
        return [bar for bar in bars if query.start_at <= bar.observed_at <= query.end_at]
