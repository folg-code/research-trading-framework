"""Unit tests for PredictiveExtraError."""

from __future__ import annotations

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive import PredictiveExtraError, PredictiveSpecError


def test_predictive_extra_error_is_validation_error_not_import_error() -> None:
    error = PredictiveExtraError(
        "estimator family 'sklearn.ridge' requires optional extra 'ml'; "
        "install with `uv sync --extra ml`"
    )
    assert isinstance(error, ValidationError)
    assert isinstance(error, Exception)
    assert not isinstance(error, ImportError)
    assert not isinstance(error, PredictiveSpecError)
    assert "ml" in str(error)
    assert "sklearn.ridge" in str(error)
