"""Continuous trade Parquet writer tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.parquet.continuous_trade_writer import (
    ParquetContinuousTradeWriter,
    continuous_trade_records_from_table,
    continuous_trade_records_to_table,
)
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.models import MarketTrade, TradeSide


def _record(*, boundary: bool) -> ContinuousTradeRecord:
    return ContinuousTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(5),
            event_at=datetime(2025, 7, 14, 14, 30, tzinfo=UTC),
            side=TradeSide.BUY,
            trade_id="t-1",
            sequence=1,
        ),
        actual_contract="NQZ5",
        product="NQ",
        session_date=date(2025, 7, 14),
        continuous_symbol="NQ_CONT",
        roll_id="roll-2",
        is_roll_boundary=boundary,
    )


def test_continuous_trade_writer_round_trip(tmp_path: Path) -> None:
    writer = ParquetContinuousTradeWriter()
    records = [_record(boundary=True)]
    path = tmp_path / "trades.parquet"

    writer.write(path, records)
    loaded = writer.read(path)

    assert loaded == records


def test_continuous_trade_table_round_trip() -> None:
    records = [_record(boundary=False), _record(boundary=True)]
    table = continuous_trade_records_to_table(records)
    loaded = continuous_trade_records_from_table(table)
    assert loaded == records
