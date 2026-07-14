"""Contract RTH volume aggregation from Arrow partition tables."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from tests.fixtures.contracts.trade_record import (
    make_contract_trade_record,
    make_rth_contract_trade_record,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.parquet.contract_rth_volumes import (
    aggregate_rth_session_volumes_from_partition_tables,
    rth_session_volume_from_trade_table,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    contract_trade_records_to_table,
)
from trading_framework.market.continuous.volumes import aggregate_rth_session_volumes
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref(contract: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(f"NQ.{contract}"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-test",
        ),
        version=1,
    )


def test_rth_session_volume_from_trade_table_matches_record_aggregator() -> None:
    session_date = date(2025, 7, 14)
    records = [
        make_rth_contract_trade_record(
            contract="NQU5",
            session_date=session_date,
            hour_utc=14,
            size=100,
        ),
        make_rth_contract_trade_record(
            contract="NQU5",
            session_date=session_date,
            hour_utc=15,
            size=50,
        ),
        make_contract_trade_record(
            second=0,
            minute=0,
            size=25,
            contract_code="NQU5",
            session_date=session_date,
            source_file="overnight.dbn.zst",
        ),
    ]
    table = contract_trade_records_to_table(records)

    record_volumes = aggregate_rth_session_volumes({"NQU5": records})
    table_volume = rth_session_volume_from_trade_table(table, session_date=session_date)

    assert table_volume == record_volumes[session_date]["NQU5"]


def test_partition_table_aggregation_matches_record_aggregator(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    repository = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    nqz5_ref = _dataset_ref("NQZ5")

    nqu5_records = [
        make_rth_contract_trade_record(
            contract="NQU5",
            session_date=date(2025, 7, 14),
            hour_utc=14,
            size=100,
        ),
        make_rth_contract_trade_record(
            contract="NQU5",
            session_date=date(2025, 7, 15),
            hour_utc=14,
            size=50,
        ),
    ]
    nqz5_records = [
        make_rth_contract_trade_record(
            contract="NQZ5",
            session_date=date(2025, 7, 14),
            hour_utc=14,
            size=10,
        ),
        make_rth_contract_trade_record(
            contract="NQZ5",
            session_date=date(2025, 7, 15),
            hour_utc=14,
            size=200,
        ),
    ]
    repository.write_records(nqu5_ref, nqu5_records)
    repository.write_records(nqz5_ref, nqz5_records)

    tables_by_contract = {
        "NQU5": [
            (date(2025, 7, 14), repository.read_session_table(nqu5_ref, date(2025, 7, 14))),
            (date(2025, 7, 15), repository.read_session_table(nqu5_ref, date(2025, 7, 15))),
        ],
        "NQZ5": [
            (date(2025, 7, 14), repository.read_session_table(nqz5_ref, date(2025, 7, 14))),
            (date(2025, 7, 15), repository.read_session_table(nqz5_ref, date(2025, 7, 15))),
        ],
    }

    record_volumes = aggregate_rth_session_volumes({"NQU5": nqu5_records, "NQZ5": nqz5_records})
    table_volumes = aggregate_rth_session_volumes_from_partition_tables(
        tables_by_contract=tables_by_contract
    )

    assert table_volumes == record_volumes
