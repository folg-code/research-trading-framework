"""Declarative model expression contracts (references, AST, validation, dependencies)."""

from trading_framework.model_expression.dependencies import (
    ExpressionDependencies,
    ExpressionDependencyExtractor,
    merge_expression_dependencies,
)
from trading_framework.model_expression.errors import (
    ModelExpressionError,
    ModelExpressionValidationError,
)
from trading_framework.model_expression.evaluation import (
    ExpressionEvaluator,
    FrameColumnResolver,
    build_evaluation_dataframe,
)
from trading_framework.model_expression.expressions import (
    MAX_EXPRESSION_DEPTH,
    AndExpression,
    CompareExpression,
    ComparisonOperator,
    Expression,
    NotExpression,
    OperandReference,
    OrExpression,
)
from trading_framework.model_expression.references import (
    ComponentOutputReference,
    MarketField,
    MarketFieldReference,
)
from trading_framework.model_expression.validation import validate_expression

__all__ = [
    "MAX_EXPRESSION_DEPTH",
    "AndExpression",
    "CompareExpression",
    "ComparisonOperator",
    "ComponentOutputReference",
    "Expression",
    "ExpressionDependencies",
    "ExpressionDependencyExtractor",
    "ExpressionEvaluator",
    "FrameColumnResolver",
    "MarketField",
    "MarketFieldReference",
    "ModelExpressionError",
    "ModelExpressionValidationError",
    "NotExpression",
    "OperandReference",
    "OrExpression",
    "build_evaluation_dataframe",
    "merge_expression_dependencies",
    "validate_expression",
]
