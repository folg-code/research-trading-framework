"""Contract trade Parquet writer tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    ParquetContractTradeWriter,
    contract_trade_records_from_table,
    contract_trade_records_to_table,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.models import MarketTrade, TradeSide


def _record(second: int = 0) -> ContractTradeRecord:
    return ContractTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(2),
            event_at=datetime(2025, 7, 13, 22, 0, second, tzinfo=UTC),
            side=TradeSide.BUY,
            trade_id="t1",
            sequence=1,
        ),
        actual_contract="NQU5",
        product="NQ",
        session_date=date(2025, 7, 13),
        source_file="sample.dbn.zst",
    )


def test_contract_trade_records_round_trip_table() -> None:
    records = [_record(0), _record(1)]
    table = contract_trade_records_to_table(records)
    restored = contract_trade_records_from_table(table)
    assert len(restored) == 2
    assert restored[0].actual_contract == "NQU5"
    assert restored[0].trade.trade_id == "t1"


def test_parquet_contract_trade_writer_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "trades.parquet"
    writer = ParquetContractTradeWriter()
    writer.write(path, [_record()])
    restored = writer.read(path)
    assert len(restored) == 1
    assert restored[0].source_file == "sample.dbn.zst"
