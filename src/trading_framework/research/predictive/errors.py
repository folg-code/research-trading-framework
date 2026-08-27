"""Validation errors for Predictive Research specification contracts and builders."""

from trading_framework.core.exceptions import ValidationError


class PredictiveSpecError(ValidationError):
    """Raised when a predictive study, feature, label, or split spec is invalid."""


class PredictiveMatrixError(PredictiveSpecError):
    """Raised when a labelled feature matrix or fold assignment cannot be built."""


class PredictiveExtraError(ValidationError):
    """Raised when a requested estimator family requires an uninstalled extra.

    The message must name the extra (``ml``, ``ml-trees``, or ``dl``) and the requested family id.
    ``ImportError`` may be chained as ``__cause__`` but must not be the raised type.
    """
