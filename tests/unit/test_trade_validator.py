"""Trade batch validator tests."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.validation.trade_validator import TradeBatchValidator
from trading_framework.market.models import MarketTrade, TradeSide


def _trade(minute: int) -> MarketTrade:
    return MarketTrade(
        price=Price(Decimal("100")),
        size=Volume(1),
        event_at=datetime(2025, 7, 13, 22, minute, tzinfo=UTC),
        side=TradeSide.BUY,
    )


def test_trade_batch_validator_accepts_ordered_batch() -> None:
    result = TradeBatchValidator().validate([_trade(0), _trade(1)])
    assert result.is_valid


def test_trade_batch_validator_rejects_unsorted_batch() -> None:
    result = TradeBatchValidator().validate([_trade(2), _trade(1)])
    assert not result.is_valid


def test_trade_batch_validator_rejects_empty_batch() -> None:
    result = TradeBatchValidator().validate([])
    assert not result.is_valid
