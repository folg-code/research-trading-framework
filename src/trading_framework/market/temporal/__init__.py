"""Bar interval timestamp conventions.

MVP convention (Sprint 002 / PRB-008 partial resolution)
--------------------------------------------------------

- ``observed_at`` is the UTC-aware interval **start**.
- ``available_at`` is the UTC-aware interval **end**, derived from ``timeframe``
  when not supplied explicitly.

CSV and provider normalization must convert foreign conventions to this canonical
pair before constructing ``MarketBar`` records.
"""

from trading_framework.market.temporal.bar_interval import (
    BarTimestampSemantics,
    derive_bar_interval,
    normalize_provider_bar_timestamp,
)

__all__ = [
    "BarTimestampSemantics",
    "derive_bar_interval",
    "normalize_provider_bar_timestamp",
]
