"""Map Databento trades rows to canonical market trades."""

from decimal import Decimal
from typing import Any

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.importers.databento.side import map_databento_trade_side
from trading_framework.market.models import MarketTrade
from trading_framework.time.models.utc_instant import require_utc_aware


def map_databento_trades_row(row: Any) -> MarketTrade:
    """Map one Databento trades DataFrame row to a ``MarketTrade``."""
    event_at = require_utc_aware(row.ts_event)
    received_raw = getattr(row, "ts_recv", None)
    received_at = require_utc_aware(received_raw) if received_raw is not None else None
    sequence_value = getattr(row, "sequence", None)
    trade_id_value = getattr(row, "trade_id", None)

    return MarketTrade(
        price=Price(Decimal(str(row.price))),
        size=Volume(int(row.size)),
        event_at=event_at,
        received_at=received_at,
        side=map_databento_trade_side(getattr(row, "side", None)),
        trade_id=str(trade_id_value) if trade_id_value is not None else None,
        sequence=int(sequence_value) if sequence_value is not None else None,
    )
