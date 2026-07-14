"""Parquet-backed continuous trade dataset repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.continuous_trade_writer import (
    ParquetContinuousTradeWriter,
)
from trading_framework.infrastructure.storage.paths import (
    dataset_contract_trades_partition_path,
    dataset_contract_trades_partitions_dir,
)
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.datasets import (
    DatasetMetadata,
    DatasetRef,
    assert_published_is_immutable,
)
from trading_framework.market.repositories import HistoricalTradeQuery


class DatasetMetadataReader(Protocol):
    """Read dataset metadata for lifecycle enforcement."""

    def get(self, dataset_ref: DatasetRef) -> DatasetMetadata: ...


class ParquetContinuousTradeDatasetRepository:
    """Persist and query continuous trades stored as session-date partitions."""

    def __init__(
        self,
        root: Path,
        writer: ParquetContinuousTradeWriter | None = None,
        metadata_reader: DatasetMetadataReader | None = None,
    ) -> None:
        self._root = root
        self._writer = writer or ParquetContinuousTradeWriter()
        self._metadata_reader = metadata_reader

    def write_session_records(
        self,
        dataset_ref: DatasetRef,
        session_date: date,
        records: Sequence[ContinuousTradeRecord],
    ) -> None:
        """Replace one session-date partition with ``records``."""
        self._assert_mutable(dataset_ref)
        path = dataset_contract_trades_partition_path(self._root, dataset_ref, session_date)
        self._writer.write(path, records)

    def read_session_records(
        self,
        dataset_ref: DatasetRef,
        session_date: date,
    ) -> list[ContinuousTradeRecord]:
        """Read one session-date partition when present."""
        path = dataset_contract_trades_partition_path(self._root, dataset_ref, session_date)
        if not path.exists():
            return []
        return self._writer.read(path)

    def query_records(self, query: HistoricalTradeQuery) -> Sequence[ContinuousTradeRecord]:
        """Return continuous records in event-time order for the requested dataset range."""
        matched: list[ContinuousTradeRecord] = []
        partitions_dir = dataset_contract_trades_partitions_dir(self._root, query.dataset_ref)
        if not partitions_dir.exists():
            return ()
        for partition_dir in sorted(partitions_dir.iterdir()):
            if not partition_dir.is_dir() or not partition_dir.name.startswith("session_date="):
                continue
            path = partition_dir / "trades.parquet"
            if not path.exists():
                continue
            for record in self._writer.read(path):
                if query.start_at <= record.trade.event_at <= query.end_at:
                    matched.append(record)
        return sorted(matched, key=lambda record: record.trade.event_at)

    def _assert_mutable(self, dataset_ref: DatasetRef) -> None:
        if self._metadata_reader is None:
            return
        metadata = self._metadata_reader.get(dataset_ref)
        try:
            assert_published_is_immutable(metadata.lifecycle_status)
        except ValidationError as exc:
            msg = "published dataset versions are immutable"
            raise ValidationError(msg) from exc
