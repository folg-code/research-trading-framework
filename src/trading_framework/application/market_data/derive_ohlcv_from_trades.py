"""Derive OHLCV bars from a published trades dataset."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.infrastructure.validation.ohlcv_validator import OhlcvBarValidator
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.derivation import DerivedOhlcvFromTradesConfig, TradesToBarsAggregator
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import (
    DatasetRepository,
    HistoricalTradeQuery,
    TradeDatasetRepository,
)
from trading_framework.market.validation import OhlcvValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


@dataclass(frozen=True, slots=True)
class DeriveOhlcvFromTradesResult:
    """Outcome of deriving OHLCV bars from published trades."""

    dataset_ref: DatasetRef
    source_dataset_ref: DatasetRef
    validation_result: ValidationResult
    bar_count: int


def _dataset_time_range(
    bars: list[MarketBar],
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    if not bars:
        return fallback, fallback
    return bars[0].observed_at, bars[-1].observed_at


def derive_ohlcv_from_trades(
    config: DerivedOhlcvFromTradesConfig,
    *,
    storage_root: Path,
    trade_repository: TradeDatasetRepository | None = None,
    bar_repository: DatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    aggregator: TradesToBarsAggregator | None = None,
    validator: OhlcvValidator | None = None,
    clock: Clock | None = None,
) -> DeriveOhlcvFromTradesResult:
    """Aggregate published trades into a WORKING derived OHLCV dataset version."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    trades_repo = trade_repository or ParquetTradeDatasetRepository(storage_root)
    bars_repo = bar_repository or ParquetDatasetRepository(storage_root)
    bars_aggregator = aggregator or TradesToBarsAggregator()
    bar_validator = validator or OhlcvBarValidator()
    utc_clock = clock or SystemClock()

    source_metadata = dataset_registry.get(config.source_dataset_ref)
    if source_metadata.data_type != "trades":
        msg = "source dataset must contain trades"
        raise ValidationError(msg)
    if source_metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
        msg = "source trades dataset must be published before derivation"
        raise ValidationError(msg)

    trades = list(
        trades_repo.query_trades(
            HistoricalTradeQuery(
                dataset_ref=config.source_dataset_ref,
                start_at=source_metadata.start_at,
                end_at=source_metadata.end_at,
            )
        )
    )
    bars = list(
        bars_aggregator.aggregate(
            trades,
            target_timeframe=config.target_timeframe,
        )
    )
    validation_result = bar_validator.validate(bars)
    validation_status = (
        ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
    )

    created_at = utc_clock.now()
    start_at, end_at = _dataset_time_range(bars, fallback=created_at)
    dataset_ref = dataset_registry.allocate_ref(config.target_dataset_id)

    if validation_result.is_valid:
        bars_repo.write_bars(dataset_ref, bars)

    metadata = DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=config.target_dataset_id.instrument_id,
        timeframe=config.target_dataset_id.timeframe,
        provider=config.target_dataset_id.provider,
        source_id=config.target_dataset_id.source_id,
        data_type=config.target_dataset_id.data_type,
        start_at=start_at,
        end_at=end_at,
        schema_version=config.schema_version,
        normalization_version=config.normalization_version,
        validation_status=validation_status,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=len(bars),
        checksum="pending",
        created_at=created_at,
        lineage=config.lineage(),
    )
    dataset_registry.register(metadata)

    return DeriveOhlcvFromTradesResult(
        dataset_ref=dataset_ref,
        source_dataset_ref=config.source_dataset_ref,
        validation_result=validation_result,
        bar_count=len(bars),
    )
