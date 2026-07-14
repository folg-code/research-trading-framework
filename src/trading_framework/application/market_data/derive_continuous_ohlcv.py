"""Derive OHLCV bars from a published continuous trades dataset."""

from __future__ import annotations

import time
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.observability.memory_stats import process_rss_mb
from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.infrastructure.storage.continuous_manifest_store import (
    read_continuous_trades_manifest,
)
from trading_framework.infrastructure.storage.continuous_ohlcv_manifest_store import (
    CONTINUOUS_OHLCV_BUILDER_VERSION,
    CONTINUOUS_OHLCV_MANIFEST_VERSION,
    ContinuousOhlcvManifest,
    read_continuous_ohlcv_manifest,
)
from trading_framework.infrastructure.storage.continuous_ohlcv_repository import (
    compute_continuous_ohlcv_source_fingerprint,
    write_dataset_continuous_ohlcv_manifest,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.continuous_trades_to_ohlcv_table import (
    continuous_trades_table_to_ohlcv_table,
    ohlcv_table_time_bounds,
)
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.parquet.writer import market_bars_from_table
from trading_framework.infrastructure.storage.paths import (
    continuous_ohlcv_manifest_path,
    continuous_trades_manifest_path,
    dataset_ohlcv_partition_path,
    list_continuous_session_dates,
    list_ohlcv_session_dates,
)
from trading_framework.infrastructure.validation.ohlcv_validator import OhlcvBarValidator
from trading_framework.market.datasets import (
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.derivation import TRADES_TO_BARS_DERIVATION_METHOD
from trading_framework.market.derivation.continuous_config import DerivedContinuousOhlcvConfig
from trading_framework.market.validation import OhlcvValidator, ValidationIssue, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock

_IMMUTABLE_LIFECYCLE = frozenset(
    {
        DatasetLifecycleState.FINALIZED,
        DatasetLifecycleState.PUBLISHED,
    }
)


@dataclass(frozen=True, slots=True)
class DeriveContinuousOhlcvResult:
    """Outcome of deriving OHLCV bars from published continuous trades."""

    dataset_ref: DatasetRef
    source_dataset_ref: DatasetRef
    roll_schedule_version: int
    validation_result: ValidationResult
    bar_count: int
    sessions_derived: tuple[date, ...] = ()
    reused: bool = False


def _sessions_to_derive(
    source_sessions: list[date],
    *,
    start_session: date,
    end_session: date,
    existing_sessions: list[date],
    rebuild_all: bool,
    rebuild_window_sessions: int,
) -> tuple[date, ...]:
    covered = tuple(
        sorted(session for session in source_sessions if start_session <= session <= end_session)
    )
    if rebuild_all or not existing_sessions:
        return covered
    if rebuild_window_sessions < 1:
        msg = "rebuild_window_sessions must be at least 1"
        raise ValidationError(msg)
    tail_start_index = max(0, len(existing_sessions) - rebuild_window_sessions)
    tail_sessions = set(existing_sessions[tail_start_index:])
    max_existing = max(existing_sessions)
    new_sessions = {session for session in covered if session > max_existing}
    return tuple(sorted(tail_sessions | new_sessions))


def _count_ohlcv_rows(storage_root: Path, dataset_ref: DatasetRef) -> int:
    total = 0
    for session_date in list_ohlcv_session_dates(storage_root, dataset_ref):
        path = dataset_ohlcv_partition_path(storage_root, dataset_ref, session_date)
        if not path.exists():
            continue
        total += pq.ParquetFile(path).metadata.num_rows  # type: ignore[no-untyped-call]
    return total


def _dataset_time_bounds(
    storage_root: Path,
    dataset_ref: DatasetRef,
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    min_at: datetime | None = None
    max_at: datetime | None = None
    for session_date in list_ohlcv_session_dates(storage_root, dataset_ref):
        path = dataset_ohlcv_partition_path(storage_root, dataset_ref, session_date)
        if not path.exists():
            continue
        table = pq.ParquetFile(path).read(columns=["observed_at"])  # type: ignore[no-untyped-call]
        session_min, session_max = ohlcv_table_time_bounds(table, fallback=fallback)
        if table.num_rows == 0:
            continue
        min_at = session_min if min_at is None else min(min_at, session_min)
        max_at = session_max if max_at is None else max(max_at, session_max)
    if min_at is None or max_at is None:
        return fallback, fallback
    return min_at, max_at


def _register_working_ohlcv_dataset(
    dataset_registry: FileDatasetRegistry,
    *,
    dataset_ref: DatasetRef,
    config: DerivedContinuousOhlcvConfig,
    created_at: datetime,
    lineage: dict[str, str],
) -> None:
    dataset_registry.register(
        DatasetMetadata(
            dataset_ref=dataset_ref,
            instrument_id=config.target_dataset_id.instrument_id,
            timeframe=config.target_dataset_id.timeframe,
            provider=config.target_dataset_id.provider,
            source_id=config.target_dataset_id.source_id,
            data_type=config.target_dataset_id.data_type,
            start_at=created_at,
            end_at=created_at,
            schema_version=config.schema_version,
            normalization_version=config.normalization_version,
            validation_status=ValidationStatus.PASSED,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=0,
            checksum="pending",
            created_at=created_at,
            lineage=lineage,
        )
    )


def _writable_ohlcv_dataset_ref(
    config: DerivedContinuousOhlcvConfig,
    *,
    storage_root: Path,
    dataset_registry: FileDatasetRegistry,
    existing_dataset_ref: DatasetRef | None,
    continuous_manifest_product: str,
    continuous_manifest_policy_slug: str,
    roll_schedule_version: int,
    utc_clock: Clock,
) -> DatasetRef:
    created_at = utc_clock.now()
    lineage = config.lineage(
        product=continuous_manifest_product,
        policy_slug=continuous_manifest_policy_slug,
        roll_schedule_version=roll_schedule_version,
    )
    if existing_dataset_ref is None:
        dataset_ref = dataset_registry.allocate_ref(config.target_dataset_id)
        _register_working_ohlcv_dataset(
            dataset_registry,
            dataset_ref=dataset_ref,
            config=config,
            created_at=created_at,
            lineage=lineage,
        )
        return dataset_ref

    existing_metadata = dataset_registry.get(existing_dataset_ref)
    if existing_metadata.lifecycle_status not in _IMMUTABLE_LIFECYCLE:
        return existing_dataset_ref

    dataset_ref = dataset_registry.allocate_ref(existing_dataset_ref.dataset_id)
    _register_working_ohlcv_dataset(
        dataset_registry,
        dataset_ref=dataset_ref,
        config=config,
        created_at=created_at,
        lineage=lineage,
    )
    timer = active_phase_timer()
    if timer is not None:
        timer.log(
            f"derive_continuous_ohlcv: allocated v{dataset_ref.version} "
            f"because v{existing_dataset_ref.version} is "
            f"{existing_metadata.lifecycle_status.value}"
        )
    return dataset_ref


def _merge_validation_results(results: list[ValidationResult]) -> ValidationResult:
    issues: list[ValidationIssue] = []
    for result in results:
        issues.extend(result.issues)
    return ValidationResult(issues=tuple(issues))


def derive_continuous_ohlcv(
    config: DerivedContinuousOhlcvConfig,
    *,
    storage_root: Path,
    continuous_repository: ParquetContinuousTradeDatasetRepository | None = None,
    bar_repository: ParquetDatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    validator: OhlcvValidator | None = None,
    clock: Clock | None = None,
    existing_dataset_ref: DatasetRef | None = None,
    reuse_if_unchanged: bool = True,
    rebuild_all: bool = False,
    rebuild_window_sessions: int = 10,
) -> DeriveContinuousOhlcvResult:
    """Aggregate published continuous trades into a partitioned derived OHLCV dataset."""
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    continuous_repo = continuous_repository or ParquetContinuousTradeDatasetRepository(
        storage_root,
        metadata_reader=dataset_registry,
    )
    bars_repo = bar_repository or ParquetDatasetRepository(
        storage_root,
        metadata_reader=dataset_registry,
    )
    bar_validator = validator or OhlcvBarValidator()
    utc_clock = clock or SystemClock()

    source_metadata = dataset_registry.get(config.source_continuous_trades_ref)
    if source_metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
        msg = "source continuous trades dataset must be published before derivation"
        raise ValidationError(msg)

    trades_manifest_path = continuous_trades_manifest_path(
        storage_root,
        config.source_continuous_trades_ref,
    )
    if not trades_manifest_path.exists():
        msg = "continuous trades manifest is required before OHLCV derivation"
        raise ValidationError(msg)
    continuous_manifest = read_continuous_trades_manifest(trades_manifest_path)
    if continuous_manifest.roll_policy_slug != config.target_dataset_id.source_id:
        msg = "continuous manifest roll policy must match target source_id"
        raise ValidationError(msg)

    source_fingerprint = compute_continuous_ohlcv_source_fingerprint(
        source_continuous_trades_ref=str(config.source_continuous_trades_ref),
        source_continuous_manifest_fingerprint=continuous_manifest.source_fingerprint,
        schema_version=config.schema_version,
        derivation_method=TRADES_TO_BARS_DERIVATION_METHOD,
        derivation_version=config.normalization_version,
        builder_version=CONTINUOUS_OHLCV_BUILDER_VERSION,
        target_timeframe=config.target_timeframe.value,
        start_session=continuous_manifest.start_session.isoformat(),
        end_session=continuous_manifest.end_session.isoformat(),
    )

    if existing_dataset_ref is not None and reuse_if_unchanged:
        manifest_path = continuous_ohlcv_manifest_path(storage_root, existing_dataset_ref)
        if manifest_path.exists() and not rebuild_all:
            existing_manifest = read_continuous_ohlcv_manifest(manifest_path)
            if existing_manifest.source_fingerprint == source_fingerprint:
                bar_count = _count_ohlcv_rows(storage_root, existing_dataset_ref)
                return DeriveContinuousOhlcvResult(
                    dataset_ref=existing_dataset_ref,
                    source_dataset_ref=config.source_continuous_trades_ref,
                    roll_schedule_version=continuous_manifest.roll_schedule_version,
                    validation_result=ValidationResult(issues=()),
                    bar_count=bar_count,
                    reused=True,
                )

    dataset_ref = _writable_ohlcv_dataset_ref(
        config,
        storage_root=storage_root,
        dataset_registry=dataset_registry,
        existing_dataset_ref=existing_dataset_ref,
        continuous_manifest_product=continuous_manifest.product,
        continuous_manifest_policy_slug=continuous_manifest.roll_policy_slug,
        roll_schedule_version=continuous_manifest.roll_schedule_version,
        utc_clock=utc_clock,
    )
    created_at = utc_clock.now()
    lineage = config.lineage(
        product=continuous_manifest.product,
        policy_slug=continuous_manifest.roll_policy_slug,
        roll_schedule_version=continuous_manifest.roll_schedule_version,
    )

    source_sessions = list_continuous_session_dates(
        storage_root,
        config.source_continuous_trades_ref,
    )
    existing_sessions = list_ohlcv_session_dates(storage_root, dataset_ref)
    sessions = _sessions_to_derive(
        source_sessions,
        start_session=continuous_manifest.start_session,
        end_session=continuous_manifest.end_session,
        existing_sessions=existing_sessions,
        rebuild_all=rebuild_all,
        rebuild_window_sessions=rebuild_window_sessions,
    )

    timer = active_phase_timer()
    if timer is not None:
        timer.log(f"derive_continuous_ohlcv: discovered {len(sessions)} sessions")

    derived_sessions: list[date] = []
    validation_results: list[ValidationResult] = []
    derive_started = time.perf_counter()

    for index, session_date in enumerate(sessions, start=1):
        session_started = time.perf_counter()
        load_context = timer.phase("derive.load") if timer is not None else nullcontext()
        load_started = time.perf_counter()
        with load_context:
            trades_table = continuous_repo.read_session_table(
                config.source_continuous_trades_ref,
                session_date,
            )
        load_seconds = time.perf_counter() - load_started
        trade_rows = trades_table.num_rows

        if trade_rows == 0:
            if timer is not None and (index == 1 or index % 10 == 0 or index == len(sessions)):
                timer.log(f"[{index}/{len(sessions)}] {session_date} trades=0 skipped")
            continue

        aggregate_context = timer.phase("derive.aggregate") if timer is not None else nullcontext()
        aggregate_started = time.perf_counter()
        with aggregate_context:
            bars_table = continuous_trades_table_to_ohlcv_table(
                trades_table,
                target_timeframe=config.target_timeframe,
            )
        aggregate_seconds = time.perf_counter() - aggregate_started
        bar_rows = bars_table.num_rows

        if bar_rows == 0:
            if timer is not None and (index == 1 or index % 10 == 0 or index == len(sessions)):
                timer.log(f"[{index}/{len(sessions)}] {session_date} trades={trade_rows} bars=0")
            continue

        session_bars = market_bars_from_table(bars_table)
        validation_results.append(bar_validator.validate(session_bars))

        write_context = timer.phase("derive.write") if timer is not None else nullcontext()
        write_started = time.perf_counter()
        with write_context:
            bars_repo.write_session_table(dataset_ref, session_date, bars_table)
        write_seconds = time.perf_counter() - write_started
        derived_sessions.append(session_date)

        if timer is not None and (index == 1 or index % 10 == 0 or index == len(sessions)):
            total_seconds = time.perf_counter() - session_started
            elapsed = time.perf_counter() - derive_started
            rss_mb = process_rss_mb()
            rss_text = f" rss_mb={rss_mb:.1f}" if rss_mb is not None else ""
            timer.log(
                f"[{index}/{len(sessions)}] {session_date} "
                f"trades={trade_rows} bars={bar_rows} "
                f"load={load_seconds:.1f}s aggregate={aggregate_seconds:.1f}s "
                f"write={write_seconds:.1f}s total={total_seconds:.1f}s "
                f"elapsed={elapsed:.1f}s{rss_text}"
            )

    validation_result = _merge_validation_results(validation_results)
    validation_status = (
        ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
    )
    bar_count = _count_ohlcv_rows(storage_root, dataset_ref)
    start_at, end_at = _dataset_time_bounds(storage_root, dataset_ref, fallback=created_at)

    manifest = ContinuousOhlcvManifest(
        manifest_version=CONTINUOUS_OHLCV_MANIFEST_VERSION,
        source_continuous_trades_ref=str(config.source_continuous_trades_ref),
        source_continuous_manifest_fingerprint=continuous_manifest.source_fingerprint,
        schema_version=config.schema_version,
        derivation_method=TRADES_TO_BARS_DERIVATION_METHOD,
        derivation_version=config.normalization_version,
        builder_version=CONTINUOUS_OHLCV_BUILDER_VERSION,
        target_timeframe=config.target_timeframe.value,
        start_session=continuous_manifest.start_session,
        end_session=continuous_manifest.end_session,
        rebuild_window_sessions=rebuild_window_sessions,
        source_fingerprint=source_fingerprint,
        created_at_utc=utc_clock.now(),
    )
    write_dataset_continuous_ohlcv_manifest(storage_root, dataset_ref, manifest)

    existing_metadata = dataset_registry.get(dataset_ref)
    dataset_registry.update(
        DatasetMetadata(
            dataset_ref=dataset_ref,
            instrument_id=existing_metadata.instrument_id,
            timeframe=existing_metadata.timeframe,
            provider=existing_metadata.provider,
            source_id=existing_metadata.source_id,
            data_type=existing_metadata.data_type,
            start_at=start_at,
            end_at=end_at,
            schema_version=existing_metadata.schema_version,
            normalization_version=existing_metadata.normalization_version,
            validation_status=validation_status,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=bar_count,
            checksum=existing_metadata.checksum,
            created_at=existing_metadata.created_at,
            lineage={
                **lineage,
                "continuous_ohlcv_manifest_fingerprint": source_fingerprint,
            },
        )
    )

    return DeriveContinuousOhlcvResult(
        dataset_ref=dataset_ref,
        source_dataset_ref=config.source_continuous_trades_ref,
        roll_schedule_version=continuous_manifest.roll_schedule_version,
        validation_result=validation_result,
        bar_count=bar_count,
        sessions_derived=tuple(derived_sessions),
        reused=False,
    )
