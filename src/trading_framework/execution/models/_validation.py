"""Shared validation helpers for execution models."""

from decimal import Decimal

from trading_framework.core.exceptions import ValidationError


def normalize_non_empty(value: str, field_name: str) -> str:
    """Normalize a non-empty string field."""
    normalized = value.strip()
    if not normalized:
        msg = f"{field_name} must be non-empty"
        raise ValidationError(msg)
    return normalized


def normalize_decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    """Normalize a finite decimal field."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not decimal_value.is_finite():
        msg = f"{field_name} must be finite"
        raise ValidationError(msg)
    return decimal_value


def normalize_positive_decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    """Normalize a strictly positive decimal field."""
    decimal_value = normalize_decimal(value, field_name)
    if decimal_value <= 0:
        msg = f"{field_name} must be positive"
        raise ValidationError(msg)
    return decimal_value


def normalize_non_negative_decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    """Normalize a non-negative decimal field."""
    decimal_value = normalize_decimal(value, field_name)
    if decimal_value < 0:
        msg = f"{field_name} must be non-negative"
        raise ValidationError(msg)
    return decimal_value
