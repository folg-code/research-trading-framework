"""User-facing condition DSL compiling to model expression IR."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from trading_framework.model_authoring.states import VolatilityState, volatility_state_compare_value
from trading_framework.model_expression.expressions import (
    AndExpression,
    BinaryCompareExpression,
    CompareExpression,
    ComparisonOperator,
    Expression,
    NotExpression,
    OperandReference,
    OrExpression,
)

if TYPE_CHECKING:
    from trading_framework.model_authoring.references.operand import Operand

CompareValue = bool | float | int | VolatilityState


def _normalize_compare_value(value: CompareValue) -> bool | float | int:
    if isinstance(value, VolatilityState):
        return volatility_state_compare_value(value)
    return value


def ensure_condition(value: "Condition | Operand") -> "Condition":
    if isinstance(value, Condition):
        return value
    return value.as_condition()


@dataclass(frozen=True, slots=True)
class Condition:
    """DSL condition node with logical operators."""

    def compile(self) -> Expression:
        msg = "abstract Condition cannot compile"
        raise NotImplementedError(msg)

    def __and__(self, other: "Condition | Operand") -> "Condition":
        return AndCondition(self, ensure_condition(other))

    def __or__(self, other: "Condition | Operand") -> "Condition":
        return OrCondition(self, ensure_condition(other))

    def __invert__(self) -> "Condition":
        return NotCondition(self)


@dataclass(frozen=True, slots=True)
class AndCondition(Condition):
    left: Condition
    right: Condition

    def compile(self) -> Expression:
        return AndExpression(left=self.left.compile(), right=self.right.compile())


@dataclass(frozen=True, slots=True)
class OrCondition(Condition):
    left: Condition
    right: Condition

    def compile(self) -> Expression:
        return OrExpression(left=self.left.compile(), right=self.right.compile())


@dataclass(frozen=True, slots=True)
class NotCondition(Condition):
    operand: Condition

    def compile(self) -> Expression:
        return NotExpression(operand=self.operand.compile())


@dataclass(frozen=True, slots=True)
class CompareCondition(Condition):
    left: OperandReference
    operator: ComparisonOperator
    value: bool | float | int

    def compile(self) -> Expression:
        return CompareExpression(
            operand=self.left,
            operator=self.operator,
            value=self.value,
        )


@dataclass(frozen=True, slots=True)
class BinaryCompareCondition(Condition):
    left: OperandReference
    operator: ComparisonOperator
    right: OperandReference

    def compile(self) -> Expression:
        return BinaryCompareExpression(
            left=self.left,
            operator=self.operator,
            right=self.right,
        )


def compare_operand_to_value(
    operand: "Operand",
    operator: ComparisonOperator,
    value: CompareValue,
) -> Condition:
    return CompareCondition(
        left=operand.reference,
        operator=operator,
        value=_normalize_compare_value(value),
    )


def compare_operands(
    left: "Operand",
    operator: ComparisonOperator,
    right: "Operand",
) -> Condition:
    return BinaryCompareCondition(
        left=left.reference,
        operator=operator,
        right=right.reference,
    )
