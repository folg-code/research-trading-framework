"""Trading session resolver protocol."""

from typing import Protocol

import polars as pl


class TradingSessionResolver(Protocol):
    """Batch map UTC timestamps to trading-session interpretation columns."""

    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        """Return columns ``timestamp``, ``trading_day``, ``session_id``, ``is_rth``."""
        ...
