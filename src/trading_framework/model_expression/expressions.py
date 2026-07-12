"""Minimal immutable expression AST for declarative models."""

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never

from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketFieldReference,
)

type OperandReference = ComponentOutputReference | MarketFieldReference


class ComparisonOperator(StrEnum):
    """Supported comparison operators for model expressions."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GE = "ge"
    LT = "lt"
    LE = "le"


@dataclass(frozen=True, slots=True)
class CompareExpression:
    """Compare one operand reference to a literal value."""

    operand: OperandReference
    operator: ComparisonOperator
    value: bool | float | int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool | int | float):
            return
        assert_never(self.value)


@dataclass(frozen=True, slots=True)
class AndExpression:
    """Logical AND of two sub-expressions."""

    left: "Expression"
    right: "Expression"


@dataclass(frozen=True, slots=True)
class OrExpression:
    """Logical OR of two sub-expressions."""

    left: "Expression"
    right: "Expression"


@dataclass(frozen=True, slots=True)
class NotExpression:
    """Logical NOT of one sub-expression."""

    operand: "Expression"


type Expression = CompareExpression | AndExpression | OrExpression | NotExpression

MAX_EXPRESSION_DEPTH = 8

__all__ = [
    "MAX_EXPRESSION_DEPTH",
    "AndExpression",
    "CompareExpression",
    "ComparisonOperator",
    "Expression",
    "NotExpression",
    "OperandReference",
    "OrExpression",
]
