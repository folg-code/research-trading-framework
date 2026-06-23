"""Dataset repository contracts."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar


@dataclass(frozen=True, slots=True)
class HistoricalBarQuery:
    """Query published or in-progress bars for a dataset version."""

    dataset_ref: DatasetRef
    start_at: datetime
    end_at: datetime


class DatasetRepository(Protocol):
    """Persist and query OHLCV bars for a dataset version."""

    def write_bars(self, dataset_ref: DatasetRef, bars: Sequence[MarketBar]) -> None:
        """Persist bars for the given dataset version."""

    def query_bars(self, query: HistoricalBarQuery) -> Sequence[MarketBar]:
        """Return bars in time order for the requested dataset range."""
