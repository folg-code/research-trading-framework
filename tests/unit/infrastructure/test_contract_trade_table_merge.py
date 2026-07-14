"""Contract trade table merge tests."""

from datetime import UTC, date, datetime

import pyarrow as pa

from tests.fixtures.contracts.trade_record import make_contract_trade_record
from trading_framework.infrastructure.storage.parquet.contract_trade_table_merge import (
    merge_contract_trade_tables,
    sort_contract_trade_table,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    MARKET_TRADE_CONTRACT_PARQUET_SCHEMA,
    MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1,
    contract_trade_records_to_table,
)


def test_merge_contract_trade_tables_sorts_by_event_time() -> None:
    first = make_contract_trade_record(second=2)
    second = make_contract_trade_record(second=0)
    third = make_contract_trade_record(second=1)
    existing = contract_trade_records_to_table([first])
    new = contract_trade_records_to_table([second, third])

    merged = merge_contract_trade_tables(existing, new)

    assert merged.num_rows == 3
    assert merged.column("ts_event_ns").to_pylist() == sorted(
        merged.column("ts_event_ns").to_pylist()
    )


def test_merge_contract_trade_tables_upgrades_legacy_schema() -> None:
    legacy = pa.table(
        {
            "price": ["22860.75"],
            "size": [2],
            "event_at": [datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC).replace(tzinfo=None)],
            "side": ["buy"],
            "received_at": [None],
            "trade_id": [None],
            "sequence": [1],
            "actual_contract": ["NQU5"],
            "product": ["NQ"],
            "session_date": [date(2025, 7, 13)],
            "source_file": ["legacy.parquet"],
        },
        schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1,
    )
    new = contract_trade_records_to_table([make_contract_trade_record(second=1)])

    merged = merge_contract_trade_tables(legacy, new)

    assert merged.schema.equals(MARKET_TRADE_CONTRACT_PARQUET_SCHEMA)
    assert merged.num_rows == 2


def test_sort_contract_trade_table_is_stable_for_single_row() -> None:
    table = contract_trade_records_to_table([make_contract_trade_record()])
    sorted_table = sort_contract_trade_table(table)
    assert sorted_table.equals(table)
