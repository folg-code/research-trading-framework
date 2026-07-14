"""Orchestrate roll schedule, continuous trades and derived OHLCV materialization."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from trading_framework.application.market_data.build_roll_schedule import (
    BuildRollScheduleRequest,
    BuildRollScheduleResult,
    build_roll_schedule,
)
from trading_framework.application.market_data.derive_continuous_ohlcv import (
    derive_continuous_ohlcv,
)
from trading_framework.application.market_data.finalize_dataset import finalize_dataset
from trading_framework.application.market_data.materialize_continuous_trades import (
    MaterializeContinuousTradesRequest,
    materialize_continuous_trades,
)
from trading_framework.application.market_data.publish_dataset import publish_dataset
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.observability.memory_stats import process_rss_mb
from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.infrastructure.storage.metadata.discovery import (
    latest_dataset_ref,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.paths import (
    list_contract_session_dates,
    roll_schedule_manifest_path,
    roll_schedule_version_dir,
)
from trading_framework.infrastructure.storage.roll_schedule_manifest_store import (
    read_roll_schedule_manifest,
)
from trading_framework.infrastructure.storage.roll_schedule_repository import (
    RollScheduleRepository,
    compute_roll_schedule_source_fingerprint,
    latest_roll_schedule_version,
)
from trading_framework.market.continuous.identity import (
    CONTINUOUS_TRADES_PROVIDER,
    continuous_instrument_id,
)
from trading_framework.market.continuous.policy import (
    VOLUME_RTH_CLOSE_POLICY_SLUG,
    VolumeRthCloseRollPolicy,
)
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetRef,
)
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    DerivedContinuousOhlcvConfig,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe

_CONTINUOUS_OHLCV_SCHEMA_VERSION = "market-bar-v1"


def _log_stage_start(timer: PhaseTimer, message: str) -> None:
    timer.log(f"{message}...")


def _log_stage(timer: PhaseTimer, message: str, *, started_at: float) -> None:
    elapsed = time.perf_counter() - started_at
    rss_mb = process_rss_mb()
    rss_text = f" rss_mb={rss_mb:.1f}" if rss_mb is not None else ""
    timer.log(f"{message} done in {elapsed:.1f}s{rss_text}")


@dataclass(frozen=True, slots=True)
class BuildContinuousRequest:
    """Input for one end-to-end continuous futures build."""

    storage_root: Path
    product: str
    contract_dataset_refs: tuple[DatasetRef, ...]
    policy_slug: str = VOLUME_RTH_CLOSE_POLICY_SLUG
    start_session: date | None = None
    end_session: date | None = None
    confirmation_sessions: int = 1
    rebuild_all: bool = False
    rebuild_window_sessions: int = 10
    publish: bool = True
    ohlcv_schema_version: str = _CONTINUOUS_OHLCV_SCHEMA_VERSION
    profile: bool = False


@dataclass(frozen=True, slots=True)
class BuildContinuousResult:
    """Outcome of one continuous futures preprocessing run."""

    roll_schedule_version: int
    continuous_trades_dataset_ref: DatasetRef
    continuous_ohlcv_dataset_ref: DatasetRef
    trades_reused: bool
    ohlcv_reused: bool
    published_trades: bool
    published_ohlcv: bool


def _session_bounds(
    storage_root: Path,
    contract_dataset_refs: tuple[DatasetRef, ...],
    *,
    start_session: date | None,
    end_session: date | None,
) -> tuple[date, date]:
    session_dates: list[date] = []
    for dataset_ref in contract_dataset_refs:
        session_dates.extend(list_contract_session_dates(storage_root, dataset_ref))
    if not session_dates:
        msg = "no contract session_date partitions found for continuous build"
        raise ValidationError(msg)
    resolved_start = start_session or min(session_dates)
    resolved_end = end_session or max(session_dates)
    if resolved_end < resolved_start:
        msg = "end_session must not be before start_session"
        raise ValidationError(msg)
    return resolved_start, resolved_end


def _resolve_roll_schedule(
    request: BuildContinuousRequest,
    *,
    registry: FileDatasetRegistry,
    clock: Clock,
) -> BuildRollScheduleResult:
    policy = VolumeRthCloseRollPolicy(
        product=request.product,
        confirmation_sessions=request.confirmation_sessions,
    )
    start_session, end_session = _session_bounds(
        request.storage_root,
        request.contract_dataset_refs,
        start_session=request.start_session,
        end_session=request.end_session,
    )
    contract_refs = tuple(str(dataset_ref) for dataset_ref in request.contract_dataset_refs)
    fingerprint = compute_roll_schedule_source_fingerprint(
        contract_dataset_refs=contract_refs,
        start_session=start_session,
        end_session=end_session,
        policy=policy,
    )
    if not request.rebuild_all:
        latest_version = latest_roll_schedule_version(
            request.storage_root,
            product=request.product,
            policy_slug=request.policy_slug,
        )
        if latest_version is not None:
            manifest_path = roll_schedule_manifest_path(
                request.storage_root,
                product=request.product,
                policy_slug=request.policy_slug,
                version=latest_version,
            )
            existing_manifest = read_roll_schedule_manifest(manifest_path)
            if existing_manifest.source_fingerprint == fingerprint:
                repository = RollScheduleRepository(request.storage_root)
                schedule, manifest = repository.read(
                    product=request.product,
                    policy_slug=request.policy_slug,
                    version=latest_version,
                    policy=policy,
                )
                return BuildRollScheduleResult(
                    schedule=schedule,
                    manifest=manifest,
                    version_dir=roll_schedule_version_dir(
                        request.storage_root,
                        product=request.product,
                        policy_slug=request.policy_slug,
                        version=latest_version,
                    ),
                )

    return build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=request.storage_root,
            product=request.product,
            contract_dataset_refs=request.contract_dataset_refs,
            start_session=request.start_session,
            end_session=request.end_session,
            confirmation_sessions=request.confirmation_sessions,
        ),
        registry=registry,
        clock=clock,
    )


def _continuous_trades_dataset_id(product: str, policy_slug: str) -> DatasetId:
    return DatasetId(
        instrument_id=continuous_instrument_id(product),
        data_type="trades",
        timeframe=Timeframe("tick"),
        provider=CONTINUOUS_TRADES_PROVIDER,
        source_id=policy_slug,
    )


def _continuous_ohlcv_dataset_id(product: str, policy_slug: str) -> DatasetId:
    return DatasetId(
        instrument_id=continuous_instrument_id(product),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider=DERIVED_OHLCV_PROVIDER,
        source_id=policy_slug,
    )


def _ensure_published_trades(
    dataset_ref: DatasetRef,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry,
    clock: Clock,
) -> bool:
    metadata = registry.get(dataset_ref)
    if metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED:
        return False
    if metadata.lifecycle_status is DatasetLifecycleState.WORKING:
        finalize_dataset(
            dataset_ref,
            storage_root=storage_root,
            registry=registry,
        )
    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=clock,
    )
    return True


def build_continuous(
    request: BuildContinuousRequest,
    *,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
) -> BuildContinuousResult:
    """Build roll schedule, continuous trades and derived OHLCV in one workflow."""
    if not request.contract_dataset_refs:
        msg = "contract_dataset_refs must not be empty"
        raise ValidationError(msg)
    if request.policy_slug != VOLUME_RTH_CLOSE_POLICY_SLUG:
        msg = f"unsupported roll policy slug: {request.policy_slug!r}"
        raise ValidationError(msg)

    dataset_registry = registry or FileDatasetRegistry(request.storage_root)
    utc_clock = clock or SystemClock()
    parent_timer = active_phase_timer()
    timer = (
        parent_timer
        if parent_timer is not None and parent_timer.enabled
        else PhaseTimer(enabled=request.profile)
    )
    owns_timer = timer is not parent_timer
    timer.log(
        f"build_continuous: product={request.product} "
        f"contracts={len(request.contract_dataset_refs)} "
        f"storage={request.storage_root}"
    )
    if owns_timer:
        timer.begin_session()

    _log_stage_start(timer, "roll_schedule")
    roll_started = time.perf_counter()
    with timer.phase("roll_schedule"):
        roll_result = _resolve_roll_schedule(
            request,
            registry=dataset_registry,
            clock=utc_clock,
        )
    _log_stage(
        timer,
        (
            f"roll_schedule v{roll_result.schedule.version} "
            f"entries={len(roll_result.schedule.entries)}"
        ),
        started_at=roll_started,
    )

    trades_dataset_id = _continuous_trades_dataset_id(request.product, request.policy_slug)
    existing_trades_ref = latest_dataset_ref(request.storage_root, trades_dataset_id)
    _log_stage_start(
        timer,
        (
            f"materialize_continuous_trades existing="
            f"{existing_trades_ref if existing_trades_ref is not None else 'none'}"
        ),
    )
    materialize_started = time.perf_counter()
    with timer.phase("materialize_continuous_trades"):
        materialize_result = materialize_continuous_trades(
            MaterializeContinuousTradesRequest(
                storage_root=request.storage_root,
                product=request.product,
                roll_schedule_version=roll_result.schedule.version,
                contract_dataset_refs=request.contract_dataset_refs,
                policy_slug=request.policy_slug,
                start_session=request.start_session,
                end_session=request.end_session,
                rebuild_all=request.rebuild_all,
                rebuild_window_sessions=request.rebuild_window_sessions,
                existing_dataset_ref=existing_trades_ref,
            ),
            registry=dataset_registry,
            clock=utc_clock,
        )
    _log_stage(
        timer,
        (
            f"materialize_continuous_trades reused={materialize_result.reused} "
            f"rows={materialize_result.record_count} "
            f"sessions={len(materialize_result.sessions_materialized)}"
        ),
        started_at=materialize_started,
    )

    published_trades = False
    if request.publish:
        _log_stage_start(
            timer,
            f"publish_continuous_trades ref={materialize_result.dataset_ref}",
        )
        publish_trades_started = time.perf_counter()
        with timer.phase("publish_continuous_trades"):
            published_trades = _ensure_published_trades(
                materialize_result.dataset_ref,
                storage_root=request.storage_root,
                registry=dataset_registry,
                clock=utc_clock,
            )
        _log_stage(
            timer,
            f"publish_continuous_trades published={published_trades}",
            started_at=publish_trades_started,
        )
    elif not materialize_result.reused:
        trades_metadata = dataset_registry.get(materialize_result.dataset_ref)
        if trades_metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
            msg = "continuous trades must be published before OHLCV derivation"
            raise ValidationError(msg)

    ohlcv_dataset_id = _continuous_ohlcv_dataset_id(request.product, request.policy_slug)
    existing_ohlcv_ref = latest_dataset_ref(request.storage_root, ohlcv_dataset_id)
    _log_stage_start(
        timer,
        (
            f"derive_continuous_ohlcv source={materialize_result.dataset_ref} "
            f"rows={materialize_result.record_count} "
            f"existing_ohlcv={existing_ohlcv_ref if existing_ohlcv_ref is not None else 'none'}"
        ),
    )
    derive_started = time.perf_counter()
    with timer.phase("derive_continuous_ohlcv"):
        derive_result = derive_continuous_ohlcv(
            DerivedContinuousOhlcvConfig(
                source_continuous_trades_ref=materialize_result.dataset_ref,
                target_dataset_id=ohlcv_dataset_id,
                schema_version=request.ohlcv_schema_version,
            ),
            storage_root=request.storage_root,
            registry=dataset_registry,
            clock=utc_clock,
            existing_dataset_ref=existing_ohlcv_ref,
            rebuild_all=request.rebuild_all,
            rebuild_window_sessions=request.rebuild_window_sessions,
        )
    ohlcv_ref = derive_result.dataset_ref
    ohlcv_reused = derive_result.reused
    derive_metadata = dataset_registry.get(ohlcv_ref)
    stage_message = (
        f"reuse_continuous_ohlcv ref={ohlcv_ref} rows={derive_metadata.row_count}"
        if derive_result.reused
        else (
            f"derive_continuous_ohlcv rows={derive_metadata.row_count} "
            f"sessions={len(derive_result.sessions_derived)}"
        )
    )
    _log_stage(timer, stage_message, started_at=derive_started)

    published_ohlcv = False
    if request.publish:
        _log_stage_start(timer, f"publish_continuous_ohlcv ref={ohlcv_ref}")
        publish_ohlcv_started = time.perf_counter()
        with timer.phase("publish_continuous_ohlcv"):
            ohlcv_metadata = dataset_registry.get(ohlcv_ref)
            if ohlcv_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED:
                published_ohlcv = False
            else:
                if ohlcv_metadata.lifecycle_status is DatasetLifecycleState.WORKING:
                    finalize_dataset(
                        ohlcv_ref,
                        storage_root=request.storage_root,
                        registry=dataset_registry,
                    )
                publish_dataset(
                    ohlcv_ref,
                    storage_root=request.storage_root,
                    registry=dataset_registry,
                    clock=utc_clock,
                )
                published_ohlcv = True
        _log_stage(
            timer,
            f"publish_continuous_ohlcv published={published_ohlcv}",
            started_at=publish_ohlcv_started,
        )

    if owns_timer:
        timer.report(title="build_continuous phase report")

    return BuildContinuousResult(
        roll_schedule_version=roll_result.schedule.version,
        continuous_trades_dataset_ref=materialize_result.dataset_ref,
        continuous_ohlcv_dataset_ref=ohlcv_ref,
        trades_reused=materialize_result.reused,
        ohlcv_reused=ohlcv_reused,
        published_trades=published_trades,
        published_ohlcv=published_ohlcv,
    )
