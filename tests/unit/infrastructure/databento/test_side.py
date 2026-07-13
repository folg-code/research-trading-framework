"""Databento side mapping tests."""

from trading_framework.infrastructure.importers.databento.side import map_databento_trade_side
from trading_framework.market.models import TradeSide


def test_map_databento_trade_side_codes() -> None:
    assert map_databento_trade_side("B") is TradeSide.BUY
    assert map_databento_trade_side("A") is TradeSide.SELL
    assert map_databento_trade_side("N") is TradeSide.UNKNOWN
    assert map_databento_trade_side(None) is TradeSide.UNKNOWN
