"""Build Signal Model definitions from the authoring DSL."""

from dataclasses import dataclass

from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.model_authoring.compile import collect_dependencies, infer_firing_policy
from trading_framework.model_authoring.conditions import Condition, ensure_condition
from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_expression.dependencies import ExpressionDependencies
from trading_framework.model_expression.expressions import Expression
from trading_framework.model_expression.validation import validate_expression
from trading_framework.signal_model.definitions import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)

LONG = SignalDirection.LONG
SHORT = SignalDirection.SHORT
NEUTRAL = SignalDirection.NEUTRAL

ON_EVENT = SignalFiringPolicy.ON_EVENT
ON_TRUE_EDGE = SignalFiringPolicy.ON_TRUE_EDGE


@dataclass(frozen=True, slots=True)
class AuthoredSignalModel:
    """User-facing Signal Model with inspectable compiled IR."""

    definition: SignalModelDefinition
    condition: Condition

    @property
    def expression(self) -> Expression:
        return self.definition.expression

    def describe(self) -> str:
        definition = self.definition
        return (
            f"SignalModel({definition.signal_model_id!r}, "
            f"direction={definition.direction.value}, "
            f"firing={definition.firing_policy.value})"
        )

    def dependencies(
        self,
        *,
        registry: ComponentRegistry | None = None,
    ) -> ExpressionDependencies:
        del registry
        return collect_dependencies(self.expression)


def signal_model(
    signal_model_id: str,
    *,
    direction: SignalDirection,
    when: Condition | Operand,
    firing: SignalFiringPolicy | None = None,
    registry: ComponentRegistry | None = None,
) -> AuthoredSignalModel:
    """Create one validated ``SignalModelDefinition`` from a DSL condition."""
    condition = ensure_condition(when)
    expression = condition.compile()
    component_registry = registry or default_mvp_registry()
    validate_expression(expression, component_registry)
    firing_policy = firing or infer_firing_policy(expression, registry=component_registry)
    definition = SignalModelDefinition(
        signal_model_id=signal_model_id,
        expression=expression,
        direction=direction,
        firing_policy=firing_policy,
    )
    return AuthoredSignalModel(definition=definition, condition=condition)
