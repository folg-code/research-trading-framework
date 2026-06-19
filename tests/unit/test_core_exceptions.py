"""Core exception hierarchy tests."""

import pytest

from trading_framework.core.exceptions import (
    ConfigurationError,
    TradingFrameworkError,
    ValidationError,
)


def test_exception_inheritance() -> None:
    assert issubclass(ValidationError, TradingFrameworkError)
    assert issubclass(ConfigurationError, TradingFrameworkError)


def test_validation_error_can_be_raised() -> None:
    with pytest.raises(ValidationError, match="invalid"):
        raise ValidationError("invalid value")
