"""Market Analysis error hierarchy."""

from trading_framework.core.exceptions import TradingFrameworkError
from trading_framework.market_analysis.identity.component import ComponentId


class MarketAnalysisError(TradingFrameworkError):
    """Base exception for Market Analysis errors."""


class PlanningError(MarketAnalysisError):
    """Raised when dependency planning fails."""


class CyclicDependencyError(PlanningError):
    """Raised when component dependencies form a cycle."""

    def __init__(self, cycle: tuple[str, ...]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(f"cyclic component dependency: {path}")


class ComponentValidationError(MarketAnalysisError):
    """Raised when component configuration or output validation fails."""

    def __init__(self, component_id: ComponentId, message: str) -> None:
        self.component_id = component_id
        super().__init__(f"{component_id}: {message}")


class OutputValidationError(ComponentValidationError):
    """Raised when an implementation returns invalid outputs."""


class ImplementationExecutionError(MarketAnalysisError):
    """Raised when a component implementation fails during execution."""

    def __init__(
        self,
        *,
        component_id: ComponentId,
        computation_key: str,
        message: str,
    ) -> None:
        self.component_id = component_id
        self.computation_key = computation_key
        super().__init__(f"{component_id} [{computation_key}]: {message}")


class CacheError(MarketAnalysisError):
    """Raised when execution cache operations fail."""
