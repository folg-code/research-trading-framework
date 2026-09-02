"""Built-in Market Analysis component registration."""

from trading_framework.market_analysis.components.candle import (
    CandleWickComponent,
    NumpyCandleWickImplementation,
)
from trading_framework.market_analysis.components.momentum import (
    NumpyRsiImplementation,
    RsiComponent,
)
from trading_framework.market_analysis.components.structure import (
    LevelDistanceComponent,
    NumpyLevelDistanceImplementation,
    NumpySessionRangeImplementation,
    NumpySwingStructureImplementation,
    SessionRangeComponent,
    SwingStructureComponent,
)
from trading_framework.market_analysis.components.trend import (
    EmaComponent,
    EmaDistanceComponent,
    NumpyEmaDistanceImplementation,
    NumpyEmaImplementation,
    NumpySlopeImplementation,
    SlopeComponent,
)
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyRangeExpansionImplementation,
    NumpyTrueRangeImplementation,
    NumpyVolatilityStateImplementation,
    RangeExpansionComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.market_analysis.registry.registry import ComponentRegistry


def register_volatility_components(registry: ComponentRegistry) -> None:
    """Register volatility feature and state components."""
    registry.register(TrueRangeComponent(), NumpyTrueRangeImplementation(), default=True)
    registry.register(AtrComponent(), NumpyAtrImplementation(), default=True)
    registry.register(
        VolatilityStateComponent(), NumpyVolatilityStateImplementation(), default=True
    )


def register_range_expansion_component(registry: ComponentRegistry) -> None:
    """Register the Range Expansion feature component."""
    registry.register(
        RangeExpansionComponent(),
        NumpyRangeExpansionImplementation(),
        default=True,
    )


def register_ema_component(registry: ComponentRegistry) -> None:
    """Register the reusable EMA feature component."""
    registry.register(EmaComponent(), NumpyEmaImplementation(), default=True)


def register_slope_component(registry: ComponentRegistry) -> None:
    """Register the reusable OLS slope feature component."""
    registry.register(SlopeComponent(), NumpySlopeImplementation(), default=True)


def register_ema_distance_component(registry: ComponentRegistry) -> None:
    """Register the EMA Distance feature component."""
    registry.register(
        EmaDistanceComponent(),
        NumpyEmaDistanceImplementation(),
        default=True,
    )


def register_swing_structure_component(registry: ComponentRegistry) -> None:
    """Register the Swing Structure component."""
    registry.register(
        SwingStructureComponent(),
        NumpySwingStructureImplementation(),
        default=True,
    )


def register_session_range_component(registry: ComponentRegistry) -> None:
    """Register the Session Range structure component."""
    registry.register(
        SessionRangeComponent(),
        NumpySessionRangeImplementation(),
        default=True,
    )


def register_candle_wick_component(registry: ComponentRegistry) -> None:
    """Register the Candle Wick feature component."""
    registry.register(CandleWickComponent(), NumpyCandleWickImplementation(), default=True)


def register_level_distance_component(registry: ComponentRegistry) -> None:
    """Register the Level Distance structure component."""
    registry.register(
        LevelDistanceComponent(),
        NumpyLevelDistanceImplementation(),
        default=True,
    )


def register_momentum_rsi_component(registry: ComponentRegistry) -> None:
    """Register the Wilder RSI momentum feature component."""
    registry.register(RsiComponent(), NumpyRsiImplementation(), default=True)


def register_mvp_components(registry: ComponentRegistry) -> None:
    """Register Sprint 003 MVP feature and state components."""
    register_volatility_components(registry)
    register_range_expansion_component(registry)
    register_ema_component(registry)
    register_ema_distance_component(registry)
    register_slope_component(registry)
    register_swing_structure_component(registry)
    register_session_range_component(registry)
    register_candle_wick_component(registry)
    register_level_distance_component(registry)
    register_momentum_rsi_component(registry)


def default_mvp_registry() -> ComponentRegistry:
    """Return a registry with all MVP components registered."""
    registry = ComponentRegistry()
    register_mvp_components(registry)
    return registry


__all__ = [
    "default_mvp_registry",
    "register_candle_wick_component",
    "register_ema_component",
    "register_ema_distance_component",
    "register_level_distance_component",
    "register_momentum_rsi_component",
    "register_mvp_components",
    "register_range_expansion_component",
    "register_session_range_component",
    "register_slope_component",
    "register_swing_structure_component",
    "register_volatility_components",
]
