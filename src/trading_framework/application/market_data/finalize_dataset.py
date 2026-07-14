"""Finalize a WORKING dataset version."""

from dataclasses import replace
from pathlib import Path

from trading_framework.application.market_data.checksum import compute_dataset_checksum
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.trade_repository_factory import (
    trade_dataset_repository_for,
)
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
    transition_dataset_lifecycle,
)
from trading_framework.market.repositories import (
    DatasetRepository,
    HistoricalBarQuery,
    HistoricalTradeQuery,
    TradeDatasetRepository,
)


def finalize_dataset(
    dataset_ref: DatasetRef,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    repository: DatasetRepository | None = None,
    trade_repository: TradeDatasetRepository | None = None,
) -> DatasetRef:
    """Transition a validated WORKING dataset version to FINALIZED."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    metadata = dataset_registry.get(dataset_ref)
    if metadata.validation_status is not ValidationStatus.PASSED:
        msg = "dataset validation must pass before finalization"
        raise ValidationError(msg)

    if metadata.data_type == "trades":
        return _finalize_trades_dataset(
            dataset_ref,
            metadata=metadata,
            dataset_registry=dataset_registry,
            trade_repository=trade_repository
            or trade_dataset_repository_for(storage_root, dataset_ref),
        )

    bar_repository = repository or ParquetDatasetRepository(storage_root)
    lifecycle_status = transition_dataset_lifecycle(
        metadata.lifecycle_status,
        DatasetLifecycleState.FINALIZED,
    )
    bars = list(
        bar_repository.query_bars(
            HistoricalBarQuery(
                dataset_ref=dataset_ref,
                start_at=metadata.start_at,
                end_at=metadata.end_at,
            )
        )
    )
    if not bars:
        msg = "dataset contains no bars to finalize"
        raise ValidationError(msg)

    updated = replace(
        metadata,
        lifecycle_status=lifecycle_status,
        row_count=len(bars),
        checksum=compute_dataset_checksum(bars),
    )
    dataset_registry.update(updated)
    return dataset_ref


def _finalize_trades_dataset(
    dataset_ref: DatasetRef,
    *,
    metadata: DatasetMetadata,
    dataset_registry: FileDatasetRegistry,
    trade_repository: TradeDatasetRepository,
) -> DatasetRef:
    lifecycle_status = transition_dataset_lifecycle(
        metadata.lifecycle_status,
        DatasetLifecycleState.FINALIZED,
    )
    trades = list(
        trade_repository.query_trades(
            HistoricalTradeQuery(
                dataset_ref=dataset_ref,
                start_at=metadata.start_at,
                end_at=metadata.end_at,
            )
        )
    )
    if not trades:
        msg = "dataset contains no trades to finalize"
        raise ValidationError(msg)

    updated = replace(
        metadata,
        lifecycle_status=lifecycle_status,
        row_count=len(trades),
    )
    dataset_registry.update(updated)
    return dataset_ref
