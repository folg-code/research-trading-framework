"""Parquet-backed dataset repository."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.writer import ParquetBarWriter
from trading_framework.infrastructure.storage.paths import dataset_bars_path
from trading_framework.market.datasets import (
    DatasetMetadata,
    DatasetRef,
    assert_published_is_immutable,
)
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import HistoricalBarQuery


class DatasetMetadataReader(Protocol):
    """Read dataset metadata for lifecycle enforcement."""

    def get(self, dataset_ref: DatasetRef) -> DatasetMetadata: ...


class ParquetDatasetRepository:
    """Persist and query OHLCV bars stored as Parquet files."""

    def __init__(
        self,
        root: Path,
        writer: ParquetBarWriter | None = None,
        metadata_reader: DatasetMetadataReader | None = None,
    ) -> None:
        self._root = root
        self._writer = writer or ParquetBarWriter()
        self._metadata_reader = metadata_reader

    def write_bars(self, dataset_ref: DatasetRef, bars: Sequence[MarketBar]) -> None:
        """Persist bars for the given dataset version."""
        if self._metadata_reader is not None:
            metadata = self._metadata_reader.get(dataset_ref)
            try:
                assert_published_is_immutable(metadata.lifecycle_status)
            except ValidationError as exc:
                msg = "published dataset versions are immutable"
                raise ValidationError(msg) from exc

        path = dataset_bars_path(self._root, dataset_ref)
        self._writer.write(path, bars)

    def query_bars(self, query: HistoricalBarQuery) -> Sequence[MarketBar]:
        """Return bars in time order for the requested dataset range."""
        path = dataset_bars_path(self._root, query.dataset_ref)
        if not path.exists():
            return []
        bars = self._writer.read(path)
        return [bar for bar in bars if query.start_at <= bar.observed_at <= query.end_at]
