"""Databento trades row mapper tests."""

from datetime import UTC, datetime
from types import SimpleNamespace

from trading_framework.infrastructure.importers.databento.mapper import map_databento_trades_row
from trading_framework.market.models import TradeSide


def test_map_databento_trades_row_builds_market_trade() -> None:
    row = SimpleNamespace(
        ts_event=datetime(2025, 7, 13, 22, 0, tzinfo=UTC),
        ts_recv=datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC),
        price=22860.75,
        size=119,
        side="B",
        sequence=7,
        trade_id="abc",
    )

    trade = map_databento_trades_row(row)
    assert trade.side is TradeSide.BUY
    assert trade.size.value == 119
    assert trade.sequence == 7
