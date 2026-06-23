"""Dependency planner errors."""

from trading_framework.core.exceptions import TradingFrameworkError


class CyclicDependencyError(TradingFrameworkError):
    """Raised when component dependencies form a cycle."""

    def __init__(self, cycle: tuple[str, ...]) -> None:
        self.cycle = cycle
        path = " -> ".join(cycle)
        super().__init__(f"cyclic component dependency: {path}")
