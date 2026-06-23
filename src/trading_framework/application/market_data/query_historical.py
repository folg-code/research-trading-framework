"""Query historical bars from a published dataset."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import DatasetLifecycleState, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository, HistoricalBarQuery


@dataclass(frozen=True, slots=True)
class QueryHistoricalRequest:
    """Consumer query for published historical bars."""

    dataset_ref: DatasetRef
    start_at: datetime
    end_at: datetime


def query_historical(
    request: QueryHistoricalRequest,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    repository: DatasetRepository | None = None,
) -> list[MarketBar]:
    """Return UTC-aware bars for a published dataset version."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    bar_repository = repository or ParquetDatasetRepository(storage_root)

    metadata = dataset_registry.get(request.dataset_ref)
    if metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
        msg = "only published datasets can be queried by consumers"
        raise ValidationError(msg)

    bars = list(
        bar_repository.query_bars(
            HistoricalBarQuery(
                dataset_ref=request.dataset_ref,
                start_at=request.start_at,
                end_at=request.end_at,
            )
        )
    )
    return sorted(bars, key=lambda bar: bar.observed_at)
