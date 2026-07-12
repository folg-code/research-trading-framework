"""Market Analysis error hierarchy tests."""

from trading_framework.market_analysis.errors import (
    CacheError,
    ComponentValidationError,
    CyclicDependencyError,
    ImplementationExecutionError,
    MarketAnalysisError,
    OutputValidationError,
    PlanningError,
)
from trading_framework.market_analysis.identity.component import ComponentId


def test_error_hierarchy_categories() -> None:
    cycle = CyclicDependencyError(("a", "b", "a"))
    assert isinstance(cycle, PlanningError)
    assert cycle.cycle == ("a", "b", "a")

    validation = ComponentValidationError(ComponentId("volatility.atr"), "invalid config")
    assert validation.component_id == ComponentId("volatility.atr")

    output = OutputValidationError(ComponentId("volatility.atr"), "bad length")
    assert isinstance(output, ComponentValidationError)

    execution = ImplementationExecutionError(
        component_id=ComponentId("volatility.atr"),
        computation_key="key",
        message="boom",
    )
    assert execution.computation_key == "key"

    cache = CacheError("cache miss policy")
    assert isinstance(cache, MarketAnalysisError)
