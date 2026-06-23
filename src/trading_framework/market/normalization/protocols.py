"""OHLCV normalization contracts."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, tzinfo
from decimal import Decimal
from typing import Protocol

from trading_framework.market.temporal import BarTimestampSemantics
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class OhlcvColumnMapping:
    """Column names in an external OHLCV file."""

    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: str


@dataclass(frozen=True, slots=True)
class OhlcvImportConfig:
    """Normalization settings for an OHLCV import."""

    column_mapping: OhlcvColumnMapping
    timeframe: Timeframe
    timestamp_semantics: BarTimestampSemantics
    source_timezone: tzinfo | None = None


@dataclass(frozen=True, slots=True)
class NormalizedBarRow:
    """Provider-independent OHLCV row ready for bar construction."""

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    observed_at: datetime
    available_at: datetime


class OhlcvNormalizer(Protocol):
    """Normalize raw OHLCV rows to canonical UTC bar inputs."""

    def normalize_row(
        self,
        raw_row: Mapping[str, str],
        config: OhlcvImportConfig,
    ) -> NormalizedBarRow:
        """Normalize one raw row from an external file."""
