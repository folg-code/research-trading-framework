"""Adapter exposing contract trades through the trade dataset repository contract."""

from __future__ import annotations

from collections.abc import Sequence

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketTrade
from trading_framework.market.repositories import HistoricalTradeQuery


class ContractTradeQueryAdapter:
    """Read contract trade partitions as ``MarketTrade`` rows for consumer queries."""

    def __init__(self, repository: ParquetContractTradeDatasetRepository) -> None:
        self._repository = repository

    def write_trades(self, dataset_ref: DatasetRef, trades: Sequence[MarketTrade]) -> None:
        """Contract consumer reads do not support trade writes through this adapter."""
        msg = "contract trade datasets must be imported via preprocessing workflows"
        raise ValidationError(msg)

    def query_trades(self, query: HistoricalTradeQuery) -> Sequence[MarketTrade]:
        """Return underlying market trades from one contract dataset version."""
        return [record.to_market_trade() for record in self._repository.query_records(query)]
