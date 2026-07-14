"""Orchestrate roll schedule, continuous trades and derived OHLCV materialization."""

from __future__ import annotations

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
from trading_framework.infrastructure.storage.metadata.discovery import (
    latest_dataset_ref,
    latest_published_dataset_ref,
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

    roll_result = _resolve_roll_schedule(
        request,
        registry=dataset_registry,
        clock=utc_clock,
    )

    trades_dataset_id = _continuous_trades_dataset_id(request.product, request.policy_slug)
    existing_trades_ref = latest_dataset_ref(request.storage_root, trades_dataset_id)
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

    published_trades = False
    if request.publish:
        published_trades = _ensure_published_trades(
            materialize_result.dataset_ref,
            storage_root=request.storage_root,
            registry=dataset_registry,
            clock=utc_clock,
        )
    elif not materialize_result.reused:
        trades_metadata = dataset_registry.get(materialize_result.dataset_ref)
        if trades_metadata.lifecycle_status is not DatasetLifecycleState.PUBLISHED:
            msg = "continuous trades must be published before OHLCV derivation"
            raise ValidationError(msg)

    ohlcv_dataset_id = _continuous_ohlcv_dataset_id(request.product, request.policy_slug)
    ohlcv_reused = False
    published_ohlcv = False
    if materialize_result.reused:
        existing_ohlcv_ref = latest_published_dataset_ref(request.storage_root, ohlcv_dataset_id)
        if existing_ohlcv_ref is None:
            msg = "reused continuous trades require a published derived OHLCV dataset"
            raise ValidationError(msg)
        ohlcv_ref = existing_ohlcv_ref
        ohlcv_reused = True
    else:
        derive_result = derive_continuous_ohlcv(
            DerivedContinuousOhlcvConfig(
                source_continuous_trades_ref=materialize_result.dataset_ref,
                target_dataset_id=ohlcv_dataset_id,
                schema_version=request.ohlcv_schema_version,
            ),
            storage_root=request.storage_root,
            registry=dataset_registry,
            clock=utc_clock,
        )
        ohlcv_ref = derive_result.dataset_ref
        if request.publish:
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

    return BuildContinuousResult(
        roll_schedule_version=roll_result.schedule.version,
        continuous_trades_dataset_ref=materialize_result.dataset_ref,
        continuous_ohlcv_dataset_ref=ohlcv_ref,
        trades_reused=materialize_result.reused,
        ohlcv_reused=ohlcv_reused,
        published_trades=published_trades,
        published_ohlcv=published_ohlcv,
    )
