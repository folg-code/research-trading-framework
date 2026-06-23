"""Built-in Market Analysis component registration."""

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


def register_mvp_components(registry: ComponentRegistry) -> None:
    """Register Sprint 003 MVP feature and state components."""
    registry.register(TrueRangeComponent(), NumpyTrueRangeImplementation(), default=True)
    registry.register(AtrComponent(), NumpyAtrImplementation(), default=True)
    registry.register(
        VolatilityStateComponent(), NumpyVolatilityStateImplementation(), default=True
    )
    registry.register(EmaComponent(), NumpyEmaImplementation(), default=True)


def default_mvp_registry() -> ComponentRegistry:
    """Return a registry with all MVP components registered."""
    registry = ComponentRegistry()
    register_mvp_components(registry)
    return registry


__all__ = ["default_mvp_registry", "register_mvp_components"]
