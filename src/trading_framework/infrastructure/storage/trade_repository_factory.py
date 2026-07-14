"""Resolve trade repositories by dataset provider."""

from __future__ import annotations

from pathlib import Path

from trading_framework.infrastructure.storage.parquet.continuous_trade_query_adapter import (
    ContinuousTradeQueryAdapter,
)
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_query_adapter import (
    ContractTradeQueryAdapter,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.market.continuous.identity import CONTINUOUS_TRADES_PROVIDER
from trading_framework.market.contracts.identity import is_contract_instrument_id
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.repositories import TradeDatasetRepository


def trade_dataset_repository_for(
    storage_root: Path,
    dataset_ref: DatasetRef,
) -> TradeDatasetRepository:
    """Return the trade repository implementation for ``dataset_ref``."""
    if dataset_ref.dataset_id.provider == CONTINUOUS_TRADES_PROVIDER:
        return ContinuousTradeQueryAdapter(
            ParquetContinuousTradeDatasetRepository(storage_root),
        )
    if is_contract_instrument_id(dataset_ref.dataset_id.instrument_id):
        return ContractTradeQueryAdapter(
            ParquetContractTradeDatasetRepository(storage_root),
        )
    return ParquetTradeDatasetRepository(storage_root)
