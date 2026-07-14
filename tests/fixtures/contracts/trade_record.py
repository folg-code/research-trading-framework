"""Contract trade record test helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from trading_framework.market.contracts.storage_codec import (
    MISSING_TS_RECV_NS,
    price_nanos_from_decimal,
    utc_ns_from_datetime,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.models import MarketTrade, TradeSide


def make_contract_trade_record(
    *,
    second: int = 0,
    minute: int = 0,
    price: Decimal = Decimal("22860.75"),
    size: int = 2,
    side: str = TradeSide.BUY.value,
    contract_code: str = "NQU5",
    product: str = "NQ",
    session_date: date | None = None,
    source_file: str = "sample.dbn.zst",
    instrument_id: int = 0,
    publisher_id: int = 0,
    sequence: int = 1,
) -> ContractTradeRecord:
    """Build one storage-ready contract trade record for tests."""
    event_at = datetime(2025, 7, 13, 22, minute, second, tzinfo=UTC)
    return ContractTradeRecord(
        ts_event_ns=utc_ns_from_datetime(event_at),
        ts_recv_ns=0,
        price_nanos=price_nanos_from_decimal(price),
        size=size,
        instrument_id=instrument_id,
        sequence=sequence,
        publisher_id=publisher_id,
        side=side,
        product=product,
        contract_code=contract_code,
        session_date=session_date or date(2025, 7, 13),
        source_file=source_file,
    )


def make_rth_contract_trade_record(
    *,
    contract: str,
    session_date: date,
    minute: int = 30,
    hour_utc: int = 14,
    second: int = 0,
    size: int = 2,
    product: str = "NQ",
    price: Decimal = Decimal("22860.75"),
    source_file: str = "sample.dbn.zst",
) -> ContractTradeRecord:
    """Build one RTH contract trade record for roll/materialization tests."""
    event_at = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        hour_utc,
        minute,
        second,
        tzinfo=UTC,
    )
    return ContractTradeRecord(
        ts_event_ns=utc_ns_from_datetime(event_at),
        ts_recv_ns=0,
        price_nanos=price_nanos_from_decimal(price),
        size=size,
        instrument_id=0,
        sequence=1,
        publisher_id=0,
        side=TradeSide.BUY.value,
        product=product,
        contract_code=contract,
        session_date=session_date,
        source_file=source_file,
    )


def make_contract_trade_record_from_market_trade(
    trade: MarketTrade,
    *,
    product: str,
    contract_code: str,
    session_date: date,
    source_file: str,
    instrument_id: int = 0,
    publisher_id: int = 0,
) -> ContractTradeRecord:
    """Bridge domain trades to storage-ready contract records in tests."""
    return ContractTradeRecord(
        ts_event_ns=utc_ns_from_datetime(trade.event_at),
        ts_recv_ns=(
            MISSING_TS_RECV_NS
            if trade.received_at is None
            else utc_ns_from_datetime(trade.received_at)
        ),
        price_nanos=price_nanos_from_decimal(trade.price.value),
        size=trade.size.value,
        instrument_id=instrument_id,
        sequence=trade.sequence or 0,
        publisher_id=publisher_id,
        side=trade.side.value,
        product=product,
        contract_code=contract_code,
        session_date=session_date,
        source_file=source_file,
    )
