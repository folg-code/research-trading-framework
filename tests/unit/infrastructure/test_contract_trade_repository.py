"""Contract trade repository tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketTrade, TradeSide
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


def _record(second: int, session_date: date) -> ContractTradeRecord:
    return ContractTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(2),
            event_at=datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC),
            side=TradeSide.BUY,
        ),
        actual_contract="NQU5",
        product="NQ",
        session_date=session_date,
        source_file="sample.dbn.zst",
    )


def test_contract_trade_repository_writes_session_date_partitions(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetContractTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    records = [_record(0, date(2025, 7, 13)), _record(1, date(2025, 7, 14))]

    repository.write_records(dataset_ref, records)

    partition_root = (
        storage_root
        / "normalized/NQ.NQU5/trades/tick/databento/nq-cme-trades-20250713/v1/partitions"
    )
    assert (partition_root / "session_date=2025-07-13/trades.parquet").exists()
    assert (partition_root / "session_date=2025-07-14/trades.parquet").exists()


def test_contract_trade_repository_queries_by_event_time_range(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetContractTradeDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    records = [_record(0, date(2025, 7, 13)), _record(1, date(2025, 7, 13))]

    repository.write_records(dataset_ref, records)
    queried = repository.query_records(
        HistoricalTradeQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC),
            end_at=datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC),
        )
    )
    assert len(queried) == 2
