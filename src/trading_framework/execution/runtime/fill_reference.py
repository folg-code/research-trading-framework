"""Fill reference helpers for dry-run execution."""

from __future__ import annotations

from trading_framework.execution.models import BestBidAskSnapshot
from trading_framework.market.models import MarketBar


def closed_bar_close_reference_quote(
    *,
    symbol: str,
    bar: MarketBar,
) -> BestBidAskSnapshot:
    """Create a zero-spread simulated fill reference from one closed bar close."""
    return BestBidAskSnapshot(
        symbol=symbol,
        bid_price=bar.close,
        ask_price=bar.close,
        event_at=bar.available_at,
        received_at=bar.available_at,
    )
