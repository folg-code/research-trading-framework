"""Validation errors for Predictive Research specification contracts."""

from trading_framework.core.exceptions import ValidationError


class PredictiveSpecError(ValidationError):
    """Raised when a predictive study, feature, label, or split spec is invalid."""
