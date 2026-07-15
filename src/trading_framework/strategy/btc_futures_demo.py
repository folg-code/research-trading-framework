"""Reusable BTC futures demo Strategy Model definitions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from trading_framework.core.exceptions import ValidationError
from trading_framework.model_authoring import LONG, ON_TRUE_EDGE, market_model, price, signal_model
from trading_framework.model_authoring.references import trend
from trading_framework.strategy.exit_model import FixedBarsExitModel
from trading_framework.strategy.risk_model import FixedQuantityRiskModel
from trading_framework.strategy.strategy_model import StrategyModelDefinition

BTC_FUTURES_DEMO_STRATEGY_MODEL_ID = "btc_futures_demo_ema_momentum"
BTC_FUTURES_DEMO_MARKET_MODEL_ID = "btc_futures_demo_market_open"
BTC_FUTURES_DEMO_SIGNAL_MODEL_ID = "btc_futures_demo_close_above_ema"
BTC_FUTURES_DEMO_DISCLOSURE = "unvalidated demo strategy model for dry-run execution only"


@dataclass(frozen=True, slots=True)
class BtcFuturesDemoStrategyConfig:
    """Parameters for the reusable BTC futures demo Strategy Model."""

    strategy_model_id: str = BTC_FUTURES_DEMO_STRATEGY_MODEL_ID
    market_model_id: str = BTC_FUTURES_DEMO_MARKET_MODEL_ID
    signal_model_id: str = BTC_FUTURES_DEMO_SIGNAL_MODEL_ID
    ema_period: int = 20
    exit_after_bars: int = 10
    quantity: Decimal = Decimal("0.001")
    disclosure: str = BTC_FUTURES_DEMO_DISCLOSURE

    def __post_init__(self) -> None:
        strategy_model_id = self.strategy_model_id.strip()
        market_model_id = self.market_model_id.strip()
        signal_model_id = self.signal_model_id.strip()
        if not strategy_model_id:
            msg = "strategy_model_id must be non-empty"
            raise ValidationError(msg)
        if not market_model_id:
            msg = "market_model_id must be non-empty"
            raise ValidationError(msg)
        if not signal_model_id:
            msg = "signal_model_id must be non-empty"
            raise ValidationError(msg)
        if self.ema_period < 2:
            msg = "ema_period must be >= 2"
            raise ValidationError(msg)
        if self.exit_after_bars < 1:
            msg = "exit_after_bars must be >= 1"
            raise ValidationError(msg)
        if self.quantity <= 0:
            msg = "quantity must be positive"
            raise ValidationError(msg)
        if "demo" not in self.disclosure.lower() or "unvalidated" not in self.disclosure.lower():
            msg = "disclosure must label the strategy as demo and unvalidated"
            raise ValidationError(msg)
        object.__setattr__(self, "strategy_model_id", strategy_model_id)
        object.__setattr__(self, "market_model_id", market_model_id)
        object.__setattr__(self, "signal_model_id", signal_model_id)


def build_btc_futures_demo_strategy_model(
    config: BtcFuturesDemoStrategyConfig | None = None,
) -> StrategyModelDefinition:
    """Build the reusable BTC futures demo Strategy Model for research and dry-run."""
    resolved = config or BtcFuturesDemoStrategyConfig()
    return StrategyModelDefinition(
        strategy_model_id=resolved.strategy_model_id,
        market_model=market_model(
            resolved.market_model_id,
            when=price.close > 0,
        ).definition,
        signal_model=signal_model(
            resolved.signal_model_id,
            direction=LONG,
            when=price.close > trend.ema(period=resolved.ema_period),
            firing=ON_TRUE_EDGE,
        ).definition,
        exit_model=FixedBarsExitModel(exit_after_bars=resolved.exit_after_bars),
        risk_model=FixedQuantityRiskModel(quantity=resolved.quantity),
    )
