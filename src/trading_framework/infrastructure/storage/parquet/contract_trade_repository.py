"""Parquet-backed contract trade dataset repository."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Protocol

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.infrastructure.storage.parquet.contract_trade_table_merge import (
    merge_contract_trade_tables,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    ParquetContractTradeWriter,
    contract_trade_columns_to_table,
    contract_trade_records_to_table,
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
        *,
        merge_existing: bool = True,
    ) -> None:
        """Persist records grouped by ``session_date`` partition."""
        self._assert_mutable(dataset_ref)
        records_by_session: dict[date, list[ContractTradeRecord]] = defaultdict(list)
        for record in records:
            records_by_session[record.session_date].append(record)
        for session_date, session_records in records_by_session.items():
            self.write_session_partition(
                dataset_ref,
                session_date,
                session_records,
                merge_existing=merge_existing,
            )

    def write_session_partition(
        self,
        dataset_ref: DatasetRef,
        session_date: date,
        records: Sequence[ContractTradeRecord],
        *,
        merge_existing: bool = True,
    ) -> None:
        """Persist one session partition, optionally merging with existing parquet."""
        self._assert_mutable(dataset_ref)
        if not records:
            return
        path = dataset_contract_trades_partition_path(self._root, dataset_ref, session_date)
        timer = active_phase_timer()
        new_table = contract_trade_records_to_table(records)
        if merge_existing and path.exists():
            if timer is not None:
                with timer.phase("parquet.read_existing"):
                    existing_table = self._writer.read_table(path)
                with timer.phase("parquet.merge_tables"):
                    merged_table = merge_contract_trade_tables(existing_table, new_table)
                with timer.phase("parquet.write_merged"):
                    self._writer.write_table(path, merged_table)
            else:
                existing_table = self._writer.read_table(path)
                merged_table = merge_contract_trade_tables(existing_table, new_table)
                self._writer.write_table(path, merged_table)
            return
        if timer is not None:
            with timer.phase("parquet.write_new"):
                self._writer.write_table(path, new_table)
        else:
            self._writer.write_table(path, new_table)

    def write_session_partition_columns(
        self,
        dataset_ref: DatasetRef,
        session_date: date,
        columns: ContractChunkColumns,
        *,
        product: str,
        contract_code: str,
        source_file: str,
        merge_existing: bool = True,
    ) -> None:
        """Persist one session partition from batch column buffers."""
        self._assert_mutable(dataset_ref)
        if len(columns) == 0:
            return
        path = dataset_contract_trades_partition_path(self._root, dataset_ref, session_date)
        timer = active_phase_timer()
        new_table = contract_trade_columns_to_table(
            columns,
            product=product,
            contract_code=contract_code,
            session_date=session_date,
            source_file=source_file,
        )
        if merge_existing and path.exists():
            if timer is not None:
                with timer.phase("parquet.read_existing"):
                    existing_table = self._writer.read_table(path)
                with timer.phase("parquet.merge_tables"):
                    merged_table = merge_contract_trade_tables(existing_table, new_table)
                with timer.phase("parquet.write_merged"):
                    self._writer.write_table(path, merged_table)
            else:
                existing_table = self._writer.read_table(path)
                merged_table = merge_contract_trade_tables(existing_table, new_table)
                self._writer.write_table(path, merged_table)
            return
        if timer is not None:
            with timer.phase("parquet.write_new"):
                self._writer.write_table(path, new_table)
        else:
            self._writer.write_table(path, new_table)

    def append_records(
        self,
        dataset_ref: DatasetRef,
        records: Sequence[ContractTradeRecord],
    ) -> None:
        """Append records without reading existing partition data."""
        self.write_records(dataset_ref, records, merge_existing=False)

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
                event_at = record.event_at()
                if query.start_at <= event_at <= query.end_at:
                    matched.append(record)
        return sorted(matched, key=lambda record: record.ts_event_ns)

    def _assert_mutable(self, dataset_ref: DatasetRef) -> None:
        if self._metadata_reader is None:
            return
        metadata = self._metadata_reader.get(dataset_ref)
        try:
            assert_published_is_immutable(metadata.lifecycle_status)
        except ValidationError as exc:
            msg = "published dataset versions are immutable"
            raise ValidationError(msg) from exc
