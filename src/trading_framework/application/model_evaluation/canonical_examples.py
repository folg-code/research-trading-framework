"""Canonical Sprint 006 Market and Signal Model examples for tests and inspection."""

from dataclasses import dataclass

from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    VolatilityState,
    market_model,
    signal_model,
    structure,
    volatility,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.time.models.timeframe import Timeframe

CANONICAL_VOLATILITY_PERIOD = 14
CANONICAL_VOLATILITY_THRESHOLD = 5.0
CANONICAL_SWING_PIVOT_RANGE = 15
CANONICAL_SWING_COMPUTATION_TIMEFRAME = Timeframe("5m")

CANONICAL_MARKET_MODEL_ID = "high_volatility"
CANONICAL_SIGNAL_HIGHER_LOW_ID = "higher_low_long"
CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID = "high_volatility_long_edge"
CANONICAL_COMBINED_SIGNAL_ID = "high_vol_and_higher_low"


def build_canonical_market_model_high_volatility(
    *,
    market_model_id: str = CANONICAL_MARKET_MODEL_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
) -> MarketModelDefinition:
    """Market Model: ``volatility.state == HIGH`` (dense high-volatility state)."""
    return market_model(
        market_model_id,
        when=(volatility.state(period=period, threshold=threshold) == VolatilityState.HIGH),
    ).definition


def build_canonical_signal_higher_low_on_event(
    *,
    signal_model_id: str = CANONICAL_SIGNAL_HIGHER_LOW_ID,
    pivot_range: int = CANONICAL_SWING_PIVOT_RANGE,
    computation_timeframe: Timeframe = CANONICAL_SWING_COMPUTATION_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``structure.swing.higher_low_event`` with ``ON_EVENT``."""
    return signal_model(
        signal_model_id,
        direction=LONG,
        when=structure.higher_low_event(
            pivot_range=pivot_range,
            timeframe=computation_timeframe,
        ),
    ).definition


def build_canonical_signal_high_volatility_on_true_edge(
    *,
    signal_model_id: str = CANONICAL_SIGNAL_HIGH_VOLATILITY_EDGE_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == HIGH`` with ``ON_TRUE_EDGE``."""
    return signal_model(
        signal_model_id,
        direction=LONG,
        when=(volatility.state(period=period, threshold=threshold) == VolatilityState.HIGH),
        firing=ON_TRUE_EDGE,
    ).definition


def build_canonical_combined_signal(
    *,
    signal_model_id: str = CANONICAL_COMBINED_SIGNAL_ID,
    period: int = CANONICAL_VOLATILITY_PERIOD,
    threshold: float = CANONICAL_VOLATILITY_THRESHOLD,
    pivot_range: int = CANONICAL_SWING_PIVOT_RANGE,
    computation_timeframe: Timeframe = CANONICAL_SWING_COMPUTATION_TIMEFRAME,
) -> SignalModelDefinition:
    """Signal Model: ``volatility.state == HIGH AND higher_low_event``."""
    return signal_model(
        signal_model_id,
        direction=LONG,
        when=(
            (volatility.state(period=period, threshold=threshold) == VolatilityState.HIGH)
            & structure.higher_low_event(
                pivot_range=pivot_range,
                timeframe=computation_timeframe,
            )
        ),
    ).definition


@dataclass(frozen=True, slots=True)
class CanonicalModelBundle:
    """All canonical Sprint 006 examples for one vertical slice."""

    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]


def build_canonical_model_bundle() -> CanonicalModelBundle:
    """Build the full canonical example set used by integration and inspection."""
    return CanonicalModelBundle(
        market_models=(build_canonical_market_model_high_volatility(),),
        signal_models=(
            build_canonical_signal_higher_low_on_event(),
            build_canonical_signal_high_volatility_on_true_edge(),
            build_canonical_combined_signal(),
        ),
    )
