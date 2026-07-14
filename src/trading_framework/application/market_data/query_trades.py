"""Query historical trades from a published dataset."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.trade_repository_factory import (
    trade_dataset_repository_for,
)
from trading_framework.market.datasets import DatasetLifecycleState, DatasetRef
from trading_framework.market.models import MarketTrade
from trading_framework.market.repositories import HistoricalTradeQuery, TradeDatasetRepository


@dataclass(frozen=True, slots=True)
class QueryTradesRequest:
    """Consumer query for published historical trades."""

    dataset_ref: DatasetRef
    start_at: datetime
    end_at: datetime


def query_trades(
    request: QueryTradesRequest,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    repository: TradeDatasetRepository | None = None,
) -> list[MarketTrade]:
    """Return UTC-aware trades for a published dataset version."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    trade_repository = repository or trade_dataset_repository_for(
        storage_root,
        request.dataset_ref,
    )

    metadata = dataset_registry.get(request.dataset_ref)
    if metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
        msg = "only published datasets can be queried by consumers"
        raise ValidationError(msg)

    return list(
        trade_repository.query_trades(
            HistoricalTradeQuery(
                dataset_ref=request.dataset_ref,
                start_at=request.start_at,
                end_at=request.end_at,
            )
        )
    )
