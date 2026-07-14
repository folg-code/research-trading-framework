"""Adapter exposing continuous trades through the trade dataset repository contract."""

from __future__ import annotations

from collections.abc import Sequence

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketTrade
from trading_framework.market.repositories import HistoricalTradeQuery


class ContinuousTradeQueryAdapter:
    """Read continuous trade partitions as ``MarketTrade`` rows for consumer queries."""

    def __init__(self, repository: ParquetContinuousTradeDatasetRepository) -> None:
        self._repository = repository

    def write_trades(self, dataset_ref: DatasetRef, trades: Sequence[MarketTrade]) -> None:
        """Continuous consumer reads do not support trade writes through this adapter."""
        msg = "continuous trade datasets must be materialized via preprocessing workflows"
        raise ValidationError(msg)

    def query_trades(self, query: HistoricalTradeQuery) -> Sequence[MarketTrade]:
        """Return underlying market trades from one continuous dataset version."""
        return [record.trade for record in self._repository.query_records(query)]
