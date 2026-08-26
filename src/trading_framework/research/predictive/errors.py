"""Validation errors for Predictive Research specification contracts and builders."""

from trading_framework.core.exceptions import ValidationError


class PredictiveSpecError(ValidationError):
    """Raised when a predictive study, feature, label, or split spec is invalid."""


class PredictiveMatrixError(PredictiveSpecError):
    """Raised when a labelled feature matrix or fold assignment cannot be built."""
