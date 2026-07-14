"""Derive OHLCV bars from a published continuous trades dataset."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.continuous_manifest_store import (
    read_continuous_trades_manifest,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.paths import continuous_trades_manifest_path
from trading_framework.infrastructure.validation.ohlcv_validator import OhlcvBarValidator
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.derivation import TradesToBarsAggregator
from trading_framework.market.derivation.continuous_config import DerivedContinuousOhlcvConfig
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository, HistoricalTradeQuery
from trading_framework.market.validation import OhlcvValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock


@dataclass(frozen=True, slots=True)
class DeriveContinuousOhlcvResult:
    """Outcome of deriving OHLCV bars from published continuous trades."""

    dataset_ref: DatasetRef
    source_dataset_ref: DatasetRef
    roll_schedule_version: int
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


def derive_continuous_ohlcv(
    config: DerivedContinuousOhlcvConfig,
    *,
    storage_root: Path,
    continuous_repository: ParquetContinuousTradeDatasetRepository | None = None,
    bar_repository: DatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    aggregator: TradesToBarsAggregator | None = None,
    validator: OhlcvValidator | None = None,
    clock: Clock | None = None,
) -> DeriveContinuousOhlcvResult:
    """Aggregate published continuous trades into a WORKING derived OHLCV dataset."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    continuous_repo = continuous_repository or ParquetContinuousTradeDatasetRepository(storage_root)
    bars_repo = bar_repository or ParquetDatasetRepository(storage_root)
    bars_aggregator = aggregator or TradesToBarsAggregator()
    bar_validator = validator or OhlcvBarValidator()
    utc_clock = clock or SystemClock()

    source_metadata = dataset_registry.get(config.source_continuous_trades_ref)
    if source_metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
        msg = "source continuous trades dataset must be published before derivation"
        raise ValidationError(msg)

    manifest_path = continuous_trades_manifest_path(
        storage_root, config.source_continuous_trades_ref
    )
    if not manifest_path.exists():
        msg = "continuous trades manifest is required before OHLCV derivation"
        raise ValidationError(msg)
    continuous_manifest = read_continuous_trades_manifest(manifest_path)
    if continuous_manifest.roll_policy_slug != config.target_dataset_id.source_id:
        msg = "continuous manifest roll policy must match target source_id"
        raise ValidationError(msg)

    trades = [
        record.trade
        for record in continuous_repo.query_records(
            HistoricalTradeQuery(
                dataset_ref=config.source_continuous_trades_ref,
                start_at=source_metadata.start_at,
                end_at=source_metadata.end_at,
            )
        )
    ]
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
    lineage = config.lineage(
        product=continuous_manifest.product,
        policy_slug=continuous_manifest.roll_policy_slug,
        roll_schedule_version=continuous_manifest.roll_schedule_version,
    )

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
        lineage=lineage,
    )
    dataset_registry.register(metadata)

    return DeriveContinuousOhlcvResult(
        dataset_ref=dataset_ref,
        source_dataset_ref=config.source_continuous_trades_ref,
        roll_schedule_version=continuous_manifest.roll_schedule_version,
        validation_result=validation_result,
        bar_count=len(bars),
    )
