"""Typed operand references for model authoring."""

from dataclasses import dataclass

from trading_framework.model_authoring.conditions import (
    CompareCondition,
    CompareValue,
    Condition,
    compare_operand_to_value,
    compare_operands,
)
from trading_framework.model_expression.expressions import ComparisonOperator, OperandReference


@dataclass(frozen=True, slots=True)
class Operand:
    """Reference to one frame operand that supports comparisons and event conditions."""

    reference: OperandReference
    is_event: bool = False

    def as_condition(self) -> Condition:
        if not self.is_event:
            msg = (
                "bare operand conditions require an event output; "
                "compare state or feature operands explicitly"
            )
            raise TypeError(msg)
        return CompareCondition(
            left=self.reference,
            operator=ComparisonOperator.EQ,
            value=True,
        )

    def __eq__(self, other: CompareValue) -> Condition:  # type: ignore[override]
        return compare_operand_to_value(self, ComparisonOperator.EQ, other)

    def __ne__(self, other: CompareValue) -> Condition:  # type: ignore[override]
        return compare_operand_to_value(self, ComparisonOperator.NE, other)

    def __gt__(self, other: "Operand | CompareValue") -> Condition:
        if isinstance(other, Operand):
            return compare_operands(self, ComparisonOperator.GT, other)
        return compare_operand_to_value(self, ComparisonOperator.GT, other)

    def __ge__(self, other: "Operand | CompareValue") -> Condition:
        if isinstance(other, Operand):
            return compare_operands(self, ComparisonOperator.GE, other)
        return compare_operand_to_value(self, ComparisonOperator.GE, other)

    def __lt__(self, other: "Operand | CompareValue") -> Condition:
        if isinstance(other, Operand):
            return compare_operands(self, ComparisonOperator.LT, other)
        return compare_operand_to_value(self, ComparisonOperator.LT, other)

    def __le__(self, other: "Operand | CompareValue") -> Condition:
        if isinstance(other, Operand):
            return compare_operands(self, ComparisonOperator.LE, other)
        return compare_operand_to_value(self, ComparisonOperator.LE, other)
