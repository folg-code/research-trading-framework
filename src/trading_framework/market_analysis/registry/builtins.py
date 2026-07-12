"""Built-in Market Analysis component registration."""

from trading_framework.market_analysis.components.structure import (
    NumpySwingStructureImplementation,
    SwingStructureComponent,
)
from trading_framework.market_analysis.components.trend import EmaComponent, NumpyEmaImplementation
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyTrueRangeImplementation,
    NumpyVolatilityStateImplementation,
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


def register_ema_component(registry: ComponentRegistry) -> None:
    """Register the reusable EMA feature component."""
    registry.register(EmaComponent(), NumpyEmaImplementation(), default=True)


def register_swing_structure_component(registry: ComponentRegistry) -> None:
    """Register the Swing Structure component."""
    registry.register(
        SwingStructureComponent(),
        NumpySwingStructureImplementation(),
        default=True,
    )


def register_mvp_components(registry: ComponentRegistry) -> None:
    """Register Sprint 003 MVP feature and state components."""
    register_volatility_components(registry)
    register_ema_component(registry)
    register_swing_structure_component(registry)


def default_mvp_registry() -> ComponentRegistry:
    """Return a registry with all MVP components registered."""
    registry = ComponentRegistry()
    register_mvp_components(registry)
    return registry


__all__ = [
    "default_mvp_registry",
    "register_ema_component",
    "register_mvp_components",
    "register_swing_structure_component",
    "register_volatility_components",
]
