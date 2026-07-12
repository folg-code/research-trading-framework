"""Model expression domain errors."""

from trading_framework.core.exceptions import TradingFrameworkError


class ModelExpressionError(TradingFrameworkError):
    """Base error for model expression contracts."""


class ModelExpressionValidationError(ModelExpressionError):
    """Raised when an expression or reference fails validation."""
