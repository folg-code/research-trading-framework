"""Contract trade Parquet writer tests."""

from datetime import UTC
from decimal import Decimal
from pathlib import Path

import pyarrow as pa

from tests.fixtures.contracts.trade_record import make_contract_trade_record
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1,
    ParquetContractTradeWriter,
    contract_trade_records_from_table,
    contract_trade_records_to_table,
)
from trading_framework.market.contracts.storage_codec import (
    decimal_price_from_nanos,
    utc_datetime_from_ns,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord


def _legacy_contract_trade_records_to_table(
    records: list[ContractTradeRecord],
) -> pa.Table:
    """Legacy multi-pass serializer retained for regression comparison."""

    def _record_to_columns(record: ContractTradeRecord) -> dict[str, object]:
        trade = record.to_market_trade()
        return {
            "price": str(trade.price.value),
            "size": trade.size.value,
            "event_at": trade.event_at.astimezone(UTC).replace(tzinfo=None),
            "side": trade.side.value,
            "received_at": (
                trade.received_at.astimezone(UTC).replace(tzinfo=None)
                if trade.received_at is not None
                else None
            ),
            "trade_id": trade.trade_id,
            "sequence": trade.sequence,
            "actual_contract": record.contract_code,
            "product": record.product,
            "session_date": record.session_date,
            "source_file": record.source_file,
        }

    return pa.table(
        {
            field.name: [_record_to_columns(record)[field.name] for record in records]
            for field in MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1
        },
        schema=MARKET_TRADE_CONTRACT_PARQUET_SCHEMA_V1,
    )


def test_contract_trade_records_round_trip_table() -> None:
    records = [make_contract_trade_record(second=0), make_contract_trade_record(second=1)]
    table = contract_trade_records_to_table(records)
    restored = contract_trade_records_from_table(table)
    assert len(restored) == 2
    assert restored[0].contract_code == "NQU5"
    assert restored[0].sequence == 1


def test_parquet_contract_trade_writer_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "trades.parquet"
    writer = ParquetContractTradeWriter()
    record = make_contract_trade_record()
    writer.write(path, [record])
    restored = writer.read(path)
    assert len(restored) == 1
    assert restored[0].source_file == "sample.dbn.zst"


def test_single_pass_serialization_matches_legacy_semantics() -> None:
    records = [make_contract_trade_record(second=0), make_contract_trade_record(second=1)]

    optimized = contract_trade_records_to_table(records)
    legacy = _legacy_contract_trade_records_to_table(records)

    optimized_rows = contract_trade_records_from_table(optimized)
    legacy_rows = contract_trade_records_from_table(legacy)

    assert len(optimized_rows) == len(legacy_rows)
    for optimized_row, legacy_row in zip(optimized_rows, legacy_rows, strict=True):
        assert optimized_row.ts_event_ns == legacy_row.ts_event_ns
        assert optimized_row.price_nanos == legacy_row.price_nanos
        assert optimized_row.size == legacy_row.size
        assert optimized_row.contract_code == legacy_row.contract_code
        assert optimized_row.session_date == legacy_row.session_date


def test_ts_event_ns_round_trip_preserves_timestamp() -> None:
    record = make_contract_trade_record(second=17, minute=31)
    restored = contract_trade_records_from_table(contract_trade_records_to_table([record]))[0]
    assert restored.ts_event_ns == record.ts_event_ns
    assert restored.event_at() == utc_datetime_from_ns(record.ts_event_ns)


def test_price_nanos_round_trip_preserves_decimal_price() -> None:
    record = make_contract_trade_record(price=Decimal("22860.75"))
    restored = contract_trade_records_from_table(contract_trade_records_to_table([record]))[0]
    assert decimal_price_from_nanos(restored.price_nanos) == Decimal("22860.75")
