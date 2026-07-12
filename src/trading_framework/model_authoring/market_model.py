"""Build Market Model definitions from the authoring DSL."""

from dataclasses import dataclass

from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_authoring.compile import collect_dependencies
from trading_framework.model_authoring.conditions import Condition, ensure_condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_expression.dependencies import ExpressionDependencies
from trading_framework.model_expression.expressions import Expression
from trading_framework.model_expression.validation import validate_expression


@dataclass(frozen=True, slots=True)
class AuthoredMarketModel:
    """User-facing Market Model with inspectable compiled IR."""

    definition: MarketModelDefinition
    condition: Condition

    @property
    def expression(self) -> Expression:
        return self.definition.expression

    def describe(self) -> str:
        return f"MarketModel({self.definition.market_model_id!r})"

    def dependencies(
        self,
        *,
        registry: ComponentRegistry | None = None,
    ) -> ExpressionDependencies:
        del registry
        return collect_dependencies(self.expression)


def market_model(
    market_model_id: str,
    *,
    when: Condition | Operand,
    registry: ComponentRegistry | None = None,
) -> AuthoredMarketModel:
    """Create one validated ``MarketModelDefinition`` from a DSL condition."""
    condition = ensure_condition(when)
    expression = condition.compile()
    component_registry = registry or default_mvp_registry()
    validate_expression(expression, component_registry)
    definition = MarketModelDefinition(
        market_model_id=market_model_id,
        expression=expression,
    )
    return AuthoredMarketModel(definition=definition, condition=condition)
