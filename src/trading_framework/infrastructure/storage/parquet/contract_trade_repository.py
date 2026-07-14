"""Parquet-backed contract trade dataset repository."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    ParquetContractTradeWriter,
)
from trading_framework.infrastructure.storage.paths import (
    dataset_contract_trades_partition_path,
    partition_days_in_range,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetMetadata,
    DatasetRef,
    assert_published_is_immutable,
)
from trading_framework.market.repositories import HistoricalTradeQuery


class DatasetMetadataReader(Protocol):
    """Read dataset metadata for lifecycle enforcement."""

    def get(self, dataset_ref: DatasetRef) -> DatasetMetadata: ...


class ParquetContractTradeDatasetRepository:
    """Persist and query contract trades stored as session-date partitions."""

    def __init__(
        self,
        root: Path,
        writer: ParquetContractTradeWriter | None = None,
        metadata_reader: DatasetMetadataReader | None = None,
    ) -> None:
        self._root = root
        self._writer = writer or ParquetContractTradeWriter()
        self._metadata_reader = metadata_reader

    def write_records(
        self,
        dataset_ref: DatasetRef,
        records: Sequence[ContractTradeRecord],
    ) -> None:
        """Persist records grouped by ``session_date`` partition."""
        self._assert_mutable(dataset_ref)
        records_by_session: dict[date, list[ContractTradeRecord]] = defaultdict(list)
        for record in records:
            records_by_session[record.session_date].append(record)

        for session_date, session_records in records_by_session.items():
            path = dataset_contract_trades_partition_path(self._root, dataset_ref, session_date)
            existing = self._writer.read(path) if path.exists() else []
            merged = [*existing, *session_records]
            self._writer.write(path, merged)

    def query_records(self, query: HistoricalTradeQuery) -> Sequence[ContractTradeRecord]:
        """Return contract records in event-time order for the requested dataset range."""
        matched: list[ContractTradeRecord] = []
        for session_date in partition_days_in_range(query.start_at, query.end_at):
            path = dataset_contract_trades_partition_path(
                self._root,
                query.dataset_ref,
                session_date,
            )
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
