"""Query historical bars from a published dataset."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pyarrow as pa

from trading_framework.application.market_data.ohlcv_columnar import (
    ohlcv_column_batch_from_table,
    sort_table_by_observed_at,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.profiling import optional_phase
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import DatasetLifecycleState, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository, HistoricalBarQuery
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch


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

    with optional_phase("ohlcv.load_metadata"):
        metadata = dataset_registry.get(request.dataset_ref)
        if metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
            msg = "only published datasets can be queried by consumers"
            raise ValidationError(msg)

    with optional_phase("ohlcv.query_bars"):
        bars = list(
            bar_repository.query_bars(
                HistoricalBarQuery(
                    dataset_ref=request.dataset_ref,
                    start_at=request.start_at,
                    end_at=request.end_at,
                )
            )
        )
    with optional_phase("ohlcv.sort_bars"):
        return sorted(bars, key=lambda bar: bar.observed_at)


def query_historical_columnar(
    request: QueryHistoricalRequest,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    repository: DatasetRepository | None = None,
) -> OhlcvColumnBatch:
    """Return sorted columnar OHLCV without materializing per-bar ``MarketBar`` objects."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    bar_repository = repository or ParquetDatasetRepository(storage_root)

    with optional_phase("ohlcv.load_metadata"):
        metadata = dataset_registry.get(request.dataset_ref)
        if metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
            msg = "only published datasets can be queried by consumers"
            raise ValidationError(msg)

    historical_query = HistoricalBarQuery(
        dataset_ref=request.dataset_ref,
        start_at=request.start_at,
        end_at=request.end_at,
    )
    with optional_phase("ohlcv.query_columnar"):
        if isinstance(bar_repository, ParquetDatasetRepository):
            table = bar_repository.query_ohlcv_table(historical_query)
        else:
            bars = list(bar_repository.query_bars(historical_query))
            table = None if not bars else _legacy_bars_to_table(bars)
    if table is None or table.num_rows == 0:
        return OhlcvColumnBatch(
            timestamps=(),
            available_at=(),
            open=(),
            high=(),
            low=(),
            close=(),
            volume=(),
        )
    with optional_phase("ohlcv.build_column_batch"):
        sorted_table = sort_table_by_observed_at(table)
        return ohlcv_column_batch_from_table(sorted_table)


def _legacy_bars_to_table(bars: list[MarketBar]) -> pa.Table:
    from trading_framework.infrastructure.storage.parquet.writer import market_bars_to_table

    return market_bars_to_table(bars)
