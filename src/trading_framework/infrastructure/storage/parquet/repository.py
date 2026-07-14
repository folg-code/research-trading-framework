"""Parquet-backed dataset repository."""

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

import pyarrow as pa

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.profiling import optional_phase
from trading_framework.infrastructure.storage.parquet.writer import (
    ParquetBarWriter,
    filter_table_by_observed_range,
    market_bars_from_table,
)
from trading_framework.infrastructure.storage.paths import (
    dataset_bars_path,
    dataset_ohlcv_partition_path,
    list_ohlcv_session_dates,
)
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

    def write_session_table(
        self,
        dataset_ref: DatasetRef,
        session_date: date,
        table: pa.Table,
    ) -> None:
        """Replace one session-date OHLCV partition from an Arrow table."""
        self._assert_mutable(dataset_ref)
        path = dataset_ohlcv_partition_path(self._root, dataset_ref, session_date)
        self._writer.write_table(path, table)

    def write_bars(self, dataset_ref: DatasetRef, bars: Sequence[MarketBar]) -> None:
        """Persist bars for the given dataset version."""
        self._assert_mutable(dataset_ref)
        path = dataset_bars_path(self._root, dataset_ref)
        self._writer.write(path, bars)

    def list_session_dates(self, dataset_ref: DatasetRef) -> list[date]:
        """Return sorted session dates with OHLCV partitions."""
        return list_ohlcv_session_dates(self._root, dataset_ref)

    def query_bars(self, query: HistoricalBarQuery) -> Sequence[MarketBar]:
        """Return bars in time order for the requested dataset range."""
        with optional_phase("ohlcv.list_session_dates"):
            session_dates = list_ohlcv_session_dates(self._root, query.dataset_ref)
        if session_dates:
            tables: list[pa.Table] = []
            with optional_phase("ohlcv.read_partition_files"):
                for session_date in session_dates:
                    path = dataset_ohlcv_partition_path(self._root, query.dataset_ref, session_date)
                    if not path.exists():
                        continue
                    tables.append(self._writer.read_table(path))
            if tables:
                with optional_phase("ohlcv.read_partitioned"):
                    combined = tables[0] if len(tables) == 1 else pa.concat_tables(tables)
                    filtered = filter_table_by_observed_range(
                        combined,
                        start_at=query.start_at,
                        end_at=query.end_at,
                    )
                    bars = market_bars_from_table(filtered)
                if bars:
                    with optional_phase("ohlcv.sort_partitioned_bars"):
                        return sorted(bars, key=lambda bar: bar.observed_at)

        path = dataset_bars_path(self._root, query.dataset_ref)
        if not path.exists():
            return []
        with optional_phase("ohlcv.read_legacy_file"):
            bars = self._writer.read(path)
        return [bar for bar in bars if query.start_at <= bar.observed_at <= query.end_at]

    def _assert_mutable(self, dataset_ref: DatasetRef) -> None:
        if self._metadata_reader is None:
            return
        metadata = self._metadata_reader.get(dataset_ref)
        try:
            assert_published_is_immutable(metadata.lifecycle_status)
        except ValidationError as exc:
            msg = "published dataset versions are immutable"
            raise ValidationError(msg) from exc
