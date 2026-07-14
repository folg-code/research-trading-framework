"""Parquet-backed trade dataset repository."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.trade_writer import ParquetTradeWriter
from trading_framework.infrastructure.storage.paths import (
    dataset_trades_partition_path,
    partition_days_in_range,
    trade_event_partition_day,
)
from trading_framework.market.datasets import (
    DatasetMetadata,
    DatasetRef,
    assert_published_is_immutable,
)
from trading_framework.market.models import MarketTrade
from trading_framework.market.repositories import HistoricalTradeQuery


class DatasetMetadataReader(Protocol):
    """Read dataset metadata for lifecycle enforcement."""

    def get(self, dataset_ref: DatasetRef) -> DatasetMetadata: ...


class ParquetTradeDatasetRepository:
    """Persist and query market trades stored as day-partitioned Parquet files."""

    def __init__(
        self,
        root: Path,
        writer: ParquetTradeWriter | None = None,
        metadata_reader: DatasetMetadataReader | None = None,
    ) -> None:
        self._root = root
        self._writer = writer or ParquetTradeWriter()
        self._metadata_reader = metadata_reader

    def write_trades(self, dataset_ref: DatasetRef, trades: Sequence[MarketTrade]) -> None:
        """Persist trades grouped by UTC day partition."""
        self._assert_mutable(dataset_ref)
        trades_by_day: dict[date, list[MarketTrade]] = defaultdict(list)
        for trade in trades:
            trades_by_day[trade_event_partition_day(trade.event_at)].append(trade)

        for day, day_trades in trades_by_day.items():
            path = dataset_trades_partition_path(self._root, dataset_ref, day)
            existing = self._writer.read(path) if path.exists() else []
            merged = [*existing, *day_trades]
            self._writer.write(path, merged)

    def query_trades(self, query: HistoricalTradeQuery) -> Sequence[MarketTrade]:
        """Return trades in event-time order for the requested dataset range."""
        matched: list[MarketTrade] = []
        for day in partition_days_in_range(query.start_at, query.end_at):
            path = dataset_trades_partition_path(self._root, query.dataset_ref, day)
            if not path.exists():
                continue
            for trade in self._writer.read(path):
                if query.start_at <= trade.event_at <= query.end_at:
                    matched.append(trade)
        return sorted(matched, key=lambda trade: trade.event_at)

    def _assert_mutable(self, dataset_ref: DatasetRef) -> None:
        if self._metadata_reader is None:
            return
        metadata = self._metadata_reader.get(dataset_ref)
        try:
            assert_published_is_immutable(metadata.lifecycle_status)
        except ValidationError as exc:
            msg = "published dataset versions are immutable"
            raise ValidationError(msg) from exc
