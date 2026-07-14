"""Databento DBN side semantics."""

from trading_framework.market.models import TradeSide


def map_databento_trade_side(raw: str | None) -> TradeSide:
    """Map Databento single-character trade side codes to canonical trade sides."""
    if raw is None:
        return TradeSide.UNKNOWN
    normalized = str(raw).strip()
    if normalized in {"", "N", "n", "None", "nan"}:
        return TradeSide.UNKNOWN
    if normalized in {"B", "b", "Bid"}:
        return TradeSide.BUY
    if normalized in {"A", "a", "Ask"}:
        return TradeSide.SELL
    return TradeSide.UNKNOWN
