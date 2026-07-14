"""Map Databento trades rows to canonical market trades."""

from typing import Any

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.importers.databento.side import map_databento_trade_side
from trading_framework.infrastructure.importers.databento.storage_normalizer import (
    DatabentoStorageTradeFields,
    map_databento_trades_row_to_storage,
)
from trading_framework.market.contracts.storage_codec import (
    decimal_price_from_nanos,
    utc_datetime_from_ns,
)
from trading_framework.market.models import MarketTrade
from trading_framework.time.models.utc_instant import require_utc_aware


def map_databento_trades_row(row: Any) -> MarketTrade:
    """Map one Databento trades DataFrame row to a ``MarketTrade``."""
    storage: DatabentoStorageTradeFields = map_databento_trades_row_to_storage(row)
    received_raw = getattr(row, "ts_recv", None)
    received_at = require_utc_aware(received_raw) if received_raw is not None else None
    trade_id_value = getattr(row, "trade_id", None)
    sequence_value = storage["sequence"]
    return MarketTrade(
        price=Price(decimal_price_from_nanos(storage["price_nanos"])),
        size=Volume(storage["size"]),
        event_at=utc_datetime_from_ns(storage["ts_event_ns"]),
        received_at=received_at,
        side=map_databento_trade_side(getattr(row, "side", None)),
        trade_id=str(trade_id_value) if trade_id_value is not None else None,
        sequence=sequence_value if sequence_value >= 0 else None,
    )
