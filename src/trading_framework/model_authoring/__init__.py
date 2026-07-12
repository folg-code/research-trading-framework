"""User-facing DSL for declarative Market and Signal models."""

from trading_framework.model_authoring.market_model import AuthoredMarketModel, market_model
from trading_framework.model_authoring.references import structure, trend, volatility
from trading_framework.model_authoring.references.price import price
from trading_framework.model_authoring.signal_model import (
    LONG,
    NEUTRAL,
    ON_EVENT,
    ON_TRUE_EDGE,
    SHORT,
    AuthoredSignalModel,
    signal_model,
)
from trading_framework.model_authoring.states import VolatilityState

__all__ = [
    "LONG",
    "NEUTRAL",
    "ON_EVENT",
    "ON_TRUE_EDGE",
    "SHORT",
    "AuthoredMarketModel",
    "AuthoredSignalModel",
    "VolatilityState",
    "market_model",
    "price",
    "signal_model",
    "structure",
    "trend",
    "volatility",
]
