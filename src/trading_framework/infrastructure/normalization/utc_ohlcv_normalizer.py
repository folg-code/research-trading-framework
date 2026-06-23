"""UTC OHLCV row normalizer."""

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, InvalidOperation

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.normalization import NormalizedBarRow, OhlcvImportConfig
from trading_framework.market.temporal import normalize_provider_bar_timestamp
from trading_framework.time.models.utc_instant import normalize_to_utc


def _parse_timestamp(value: str, config: OhlcvImportConfig) -> datetime:
    stripped = value.strip()
    if not stripped:
        msg = "timestamp value must be non-empty"
        raise ValidationError(msg)

    try:
        parsed = datetime.fromisoformat(stripped)
    except ValueError as exc:
        msg = f"unsupported timestamp format: {value!r}"
        raise ValidationError(msg) from exc

    return normalize_to_utc(parsed, config.source_timezone)


def _parse_decimal(value: str, field: str) -> Decimal:
    stripped = value.strip()
    if not stripped:
        msg = f"{field} must be non-empty"
        raise ValidationError(msg)
    try:
        return Decimal(stripped)
    except InvalidOperation as exc:
        msg = f"invalid decimal for {field}: {value!r}"
        raise ValidationError(msg) from exc


def _parse_volume(value: str) -> int:
    stripped = value.strip()
    if not stripped:
        msg = "volume must be non-empty"
        raise ValidationError(msg)
    try:
        volume = int(stripped)
    except ValueError as exc:
        msg = f"invalid volume: {value!r}"
        raise ValidationError(msg) from exc
    if volume < 0:
        msg = "volume must be non-negative"
        raise ValidationError(msg)
    return volume


def _required_field(raw_row: Mapping[str, str], column: str) -> str:
    if column not in raw_row:
        msg = f"missing required column: {column}"
        raise ValidationError(msg)
    return raw_row[column]


class UtcOhlcvNormalizer:
    """Normalize external OHLCV rows to canonical UTC bar inputs."""

    def normalize_row(
        self,
        raw_row: Mapping[str, str],
        config: OhlcvImportConfig,
    ) -> NormalizedBarRow:
        """Normalize one raw row from an external file."""
        mapping = config.column_mapping
        timestamp = _parse_timestamp(_required_field(raw_row, mapping.timestamp), config)
        observed_at, available_at = normalize_provider_bar_timestamp(
            timestamp,
            timeframe=config.timeframe,
            semantics=config.timestamp_semantics,
        )
        return NormalizedBarRow(
            open=_parse_decimal(_required_field(raw_row, mapping.open), "open"),
            high=_parse_decimal(_required_field(raw_row, mapping.high), "high"),
            low=_parse_decimal(_required_field(raw_row, mapping.low), "low"),
            close=_parse_decimal(_required_field(raw_row, mapping.close), "close"),
            volume=_parse_volume(_required_field(raw_row, mapping.volume)),
            observed_at=observed_at,
            available_at=available_at,
        )
