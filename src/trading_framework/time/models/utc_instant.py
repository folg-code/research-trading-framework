"""UTC timestamp normalization utilities."""

from datetime import UTC, datetime, tzinfo

from trading_framework.core.exceptions import ValidationError


def require_utc_aware(value: datetime) -> datetime:
    """Return a UTC-aware datetime, rejecting naive values."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        msg = "timestamp must be timezone-aware"
        raise ValidationError(msg)
    return value.astimezone(UTC)


def normalize_to_utc(value: datetime, source_tz: tzinfo | None = None) -> datetime:
    """Normalize an aware datetime to UTC."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        if source_tz is None:
            msg = "naive timestamp requires source_tz for normalization"
            raise ValidationError(msg)
        value = value.replace(tzinfo=source_tz)
    return value.astimezone(UTC)
