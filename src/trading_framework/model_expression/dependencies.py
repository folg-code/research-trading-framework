"""Extract Market Analysis dependencies from model expressions."""

from dataclasses import dataclass

from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.model_expression.expressions import (
    AndExpression,
    CompareExpression,
    Expression,
    NotExpression,
    OrExpression,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
)


@dataclass(frozen=True, slots=True)
class ExpressionDependencies:
    """Deterministic dependency set required to evaluate one expression."""

    component_requests: tuple[ComponentRequest, ...]
    market_fields: tuple[MarketField, ...]


class ExpressionDependencyExtractor:
    """Collect deduplicated analysis dependencies from one expression tree."""

    def extract(self, expression: Expression) -> ExpressionDependencies:
        component_requests: dict[str, ComponentRequest] = {}
        market_fields: dict[str, MarketField] = {}
        self._visit(expression, component_requests, market_fields)
        return ExpressionDependencies(
            component_requests=tuple(component_requests[key] for key in sorted(component_requests)),
            market_fields=tuple(market_fields[key] for key in sorted(market_fields)),
        )

    def _visit(
        self,
        expression: Expression,
        component_requests: dict[str, ComponentRequest],
        market_fields: dict[str, MarketField],
    ) -> None:
        if isinstance(expression, CompareExpression):
            self._visit_operand(expression.operand, component_requests, market_fields)
            return

        if isinstance(expression, AndExpression):
            self._visit(expression.left, component_requests, market_fields)
            self._visit(expression.right, component_requests, market_fields)
            return

        if isinstance(expression, OrExpression):
            self._visit(expression.left, component_requests, market_fields)
            self._visit(expression.right, component_requests, market_fields)
            return

        if isinstance(expression, NotExpression):
            self._visit(expression.operand, component_requests, market_fields)
            return

    def _visit_operand(
        self,
        operand: ComponentOutputReference | MarketFieldReference,
        component_requests: dict[str, ComponentRequest],
        market_fields: dict[str, MarketField],
    ) -> None:
        if isinstance(operand, MarketFieldReference):
            market_fields[operand.field.value] = operand.field
            return

        request = operand.to_component_request()
        component_requests[operand.dependency_key()] = request


__all__ = ["ExpressionDependencies", "ExpressionDependencyExtractor"]
