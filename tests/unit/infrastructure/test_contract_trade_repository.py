"""Contract trade repository tests."""

from datetime import UTC, date, datetime
from pathlib import Path

from tests.fixtures.contracts.trade_record import make_contract_trade_record
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    ParquetContractTradeWriter,
)
from trading_framework.infrastructure.storage.paths import dataset_contract_trades_partition_path
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.repositories import HistoricalTradeQuery
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.NQU5"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-20250713",
        ),
        version=1,
    )


def test_contract_trade_repository_writes_session_date_partitions(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetContractTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    records = [
        make_contract_trade_record(second=0, session_date=date(2025, 7, 13)),
        make_contract_trade_record(second=1, session_date=date(2025, 7, 14)),
    ]

    repository.write_records(dataset_ref, records)

    assert dataset_contract_trades_partition_path(
        storage_root,
        dataset_ref,
        date(2025, 7, 13),
    ).exists()
    assert dataset_contract_trades_partition_path(
        storage_root,
        dataset_ref,
        date(2025, 7, 14),
    ).exists()


def test_contract_trade_repository_merges_partitions_without_domain_round_trip(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    writer = ParquetContractTradeWriter()
    repository = ParquetContractTradeDatasetRepository(storage_root, writer=writer)
    dataset_ref = _dataset_ref()
    first_batch = [make_contract_trade_record(second=0, session_date=date(2025, 7, 13))]
    second_batch = [make_contract_trade_record(second=1, session_date=date(2025, 7, 13))]

    repository.write_session_partition(
        dataset_ref,
        date(2025, 7, 13),
        first_batch,
        merge_existing=False,
    )
    repository.write_session_partition(
        dataset_ref,
        date(2025, 7, 13),
        second_batch,
        merge_existing=True,
    )

    partition_path = dataset_contract_trades_partition_path(
        storage_root,
        dataset_ref,
        date(2025, 7, 13),
    )
    merged_table = writer.read_table(partition_path)
    assert merged_table.num_rows == 2


def test_contract_trade_repository_queries_by_event_time_range(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetContractTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    records = [
        make_contract_trade_record(second=0, session_date=date(2025, 7, 13)),
        make_contract_trade_record(second=1, session_date=date(2025, 7, 13)),
    ]

    repository.write_records(dataset_ref, records)
    queried = repository.query_records(
        HistoricalTradeQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC),
            end_at=datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC),
        )
    )
    assert len(queried) == 2
