"""Materialize continuous trades from contract datasets and a roll schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.continuous_manifest_store import (
    CONTINUOUS_MANIFEST_VERSION,
    ContinuousTradesManifest,
    read_continuous_trades_manifest,
)
from trading_framework.infrastructure.storage.continuous_trades_repository import (
    compute_continuous_source_fingerprint,
    write_dataset_continuous_manifest,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    ParquetContractTradeWriter,
)
from trading_framework.infrastructure.storage.paths import (
    continuous_trades_manifest_path,
    dataset_contract_trades_partition_path,
    list_continuous_session_dates,
)
from trading_framework.infrastructure.storage.roll_schedule_repository import RollScheduleRepository
from trading_framework.market.continuous.identity import (
    CONTINUOUS_BUILDER_VERSION,
    CONTINUOUS_TRADES_PROVIDER,
    continuous_instrument_id,
)
from trading_framework.market.continuous.materializer import (
    materialize_session_records,
    sessions_covered_by_schedule,
)
from trading_framework.market.continuous.policy import (
    VOLUME_RTH_CLOSE_POLICY_SLUG,
    VolumeRthCloseRollPolicy,
)
from trading_framework.market.continuous.schedule import RollSchedule
from trading_framework.market.continuous.trade_record import MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class MaterializeContinuousTradesRequest:
    """Input for materializing one continuous trades dataset version."""

    storage_root: Path
    product: str
    roll_schedule_version: int
    contract_dataset_refs: tuple[DatasetRef, ...]
    policy_slug: str = VOLUME_RTH_CLOSE_POLICY_SLUG
    start_session: date | None = None
    end_session: date | None = None
    rebuild_all: bool = False
    rebuild_window_sessions: int = 10
    existing_dataset_ref: DatasetRef | None = None
    reuse_if_unchanged: bool = True


@dataclass(frozen=True, slots=True)
class MaterializeContinuousTradesResult:
    """Outcome of one continuous trades materialization."""

    dataset_ref: DatasetRef
    manifest: ContinuousTradesManifest
    sessions_materialized: tuple[date, ...]
    record_count: int
    reused: bool


def _contract_code_from_dataset_ref(dataset_ref: DatasetRef) -> str:
    instrument = dataset_ref.dataset_id.instrument_id.value
    if "." not in instrument:
        msg = f"contract dataset instrument must be PRODUCT.CONTRACT, got {instrument!r}"
        raise ValidationError(msg)
    return instrument.split(".", 1)[1]


def _contract_refs_by_code(
    contract_dataset_refs: tuple[DatasetRef, ...],
) -> dict[str, DatasetRef]:
    mapping: dict[str, DatasetRef] = {}
    for dataset_ref in contract_dataset_refs:
        mapping[_contract_code_from_dataset_ref(dataset_ref)] = dataset_ref
    return mapping


def _load_contract_session_records(
    storage_root: Path,
    dataset_ref: DatasetRef,
    session_date: date,
    *,
    writer: ParquetContractTradeWriter,
) -> list[ContractTradeRecord]:
    path = dataset_contract_trades_partition_path(storage_root, dataset_ref, session_date)
    if not path.exists():
        return []
    return writer.read(path)


def _sessions_to_materialize(
    schedule: RollSchedule,
    *,
    start_session: date,
    end_session: date,
    existing_sessions: list[date],
    rebuild_all: bool,
    rebuild_window_sessions: int,
) -> tuple[date, ...]:
    covered = sessions_covered_by_schedule(
        schedule,
        start_session=start_session,
        end_session=end_session,
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


def _count_dataset_records(
    storage_root: Path,
    repository: ParquetContinuousTradeDatasetRepository,
    dataset_ref: DatasetRef,
) -> int:
    total = 0
    for session_date in list_continuous_session_dates(storage_root, dataset_ref):
        total += len(repository.read_session_records(dataset_ref, session_date))
    return total


def _dataset_time_bounds(
    storage_root: Path,
    repository: ParquetContinuousTradeDatasetRepository,
    dataset_ref: DatasetRef,
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    event_times: list[datetime] = []
    for session_date in list_continuous_session_dates(storage_root, dataset_ref):
        for record in repository.read_session_records(dataset_ref, session_date):
            event_times.append(record.trade.event_at)
    if not event_times:
        return fallback, fallback
    return min(event_times), max(event_times)


def materialize_continuous_trades(
    request: MaterializeContinuousTradesRequest,
    *,
    registry: FileDatasetRegistry | None = None,
    roll_repository: RollScheduleRepository | None = None,
    continuous_repository: ParquetContinuousTradeDatasetRepository | None = None,
    contract_writer: ParquetContractTradeWriter | None = None,
    clock: Clock | None = None,
) -> MaterializeContinuousTradesResult:
    """Stitch contract trades into a versioned continuous trades dataset."""
    if not request.contract_dataset_refs:
        msg = "contract_dataset_refs must not be empty"
        raise ValidationError(msg)

    dataset_registry = registry or FileDatasetRegistry(request.storage_root)
    schedule_repository = roll_repository or RollScheduleRepository(request.storage_root)
    continuous_repo = continuous_repository or ParquetContinuousTradeDatasetRepository(
        request.storage_root,
        metadata_reader=dataset_registry,
    )
    contract_trade_writer = contract_writer or ParquetContractTradeWriter()
    utc_clock = clock or SystemClock()

    policy = VolumeRthCloseRollPolicy(product=request.product)
    if request.policy_slug != policy.slug:
        msg = f"unsupported roll policy slug: {request.policy_slug!r}"
        raise ValidationError(msg)

    schedule, roll_manifest = schedule_repository.read(
        product=request.product,
        policy_slug=request.policy_slug,
        version=request.roll_schedule_version,
        policy=policy,
    )
    start_session = request.start_session or roll_manifest.start_session
    end_session = request.end_session or roll_manifest.end_session
    if end_session < start_session:
        msg = "end_session must not be before start_session"
        raise ValidationError(msg)

    contract_refs = tuple(str(dataset_ref) for dataset_ref in request.contract_dataset_refs)
    source_fingerprint = compute_continuous_source_fingerprint(
        roll_schedule_fingerprint=roll_manifest.source_fingerprint,
        roll_schedule_version=schedule.version,
        contract_dataset_refs=contract_refs,
        schema_version=MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION,
        builder_version=CONTINUOUS_BUILDER_VERSION,
        policy_slug=request.policy_slug,
        start_session=start_session,
        end_session=end_session,
    )

    if request.existing_dataset_ref is not None and request.reuse_if_unchanged:
        manifest_path = continuous_trades_manifest_path(
            request.storage_root,
            request.existing_dataset_ref,
        )
        if manifest_path.exists() and not request.rebuild_all:
            existing_manifest = read_continuous_trades_manifest(manifest_path)
            if existing_manifest.source_fingerprint == source_fingerprint:
                record_count = _count_dataset_records(
                    request.storage_root,
                    continuous_repo,
                    request.existing_dataset_ref,
                )
                return MaterializeContinuousTradesResult(
                    dataset_ref=request.existing_dataset_ref,
                    manifest=existing_manifest,
                    sessions_materialized=(),
                    record_count=record_count,
                    reused=True,
                )

    dataset_ref = request.existing_dataset_ref
    created_at = utc_clock.now()
    if dataset_ref is None:
        dataset_ref = dataset_registry.allocate_ref(
            DatasetId(
                instrument_id=continuous_instrument_id(request.product),
                data_type="trades",
                timeframe=Timeframe("tick"),
                provider=CONTINUOUS_TRADES_PROVIDER,
                source_id=request.policy_slug,
            )
        )
        start_at, end_at = created_at, created_at
        dataset_registry.register(
            DatasetMetadata(
                dataset_ref=dataset_ref,
                instrument_id=dataset_ref.dataset_id.instrument_id,
                timeframe=dataset_ref.dataset_id.timeframe,
                provider=dataset_ref.dataset_id.provider,
                source_id=dataset_ref.dataset_id.source_id,
                data_type=dataset_ref.dataset_id.data_type,
                start_at=start_at,
                end_at=end_at,
                schema_version=MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION,
                normalization_version=CONTINUOUS_BUILDER_VERSION,
                validation_status=ValidationStatus.PASSED,
                lifecycle_status=DatasetLifecycleState.WORKING,
                row_count=0,
                checksum="pending",
                created_at=created_at,
                lineage={
                    "roll_schedule_version": str(schedule.version),
                    "roll_schedule_fingerprint": roll_manifest.source_fingerprint,
                },
            )
        )

    contract_refs_by_code = _contract_refs_by_code(request.contract_dataset_refs)
    existing_sessions = list_continuous_session_dates(request.storage_root, dataset_ref)
    sessions = _sessions_to_materialize(
        schedule,
        start_session=start_session,
        end_session=end_session,
        existing_sessions=existing_sessions,
        rebuild_all=request.rebuild_all,
        rebuild_window_sessions=request.rebuild_window_sessions,
    )

    for session_date in sessions:
        active_contract = schedule.active_contract_for_session(session_date)
        if active_contract is None:
            continue
        contract_ref = contract_refs_by_code.get(active_contract)
        if contract_ref is None:
            msg = f"missing contract dataset for active contract {active_contract!r}"
            raise ValidationError(msg)
        contract_records = _load_contract_session_records(
            request.storage_root,
            contract_ref,
            session_date,
            writer=contract_trade_writer,
        )
        continuous_records = materialize_session_records(
            schedule,
            session_date=session_date,
            contract_records=contract_records,
        )
        continuous_repo.write_session_records(dataset_ref, session_date, continuous_records)

    record_count = _count_dataset_records(request.storage_root, continuous_repo, dataset_ref)
    start_at, end_at = _dataset_time_bounds(
        request.storage_root,
        continuous_repo,
        dataset_ref,
        fallback=created_at,
    )
    manifest = ContinuousTradesManifest(
        manifest_version=CONTINUOUS_MANIFEST_VERSION,
        product=request.product,
        schema="trades",
        schema_version=MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION,
        roll_policy_slug=request.policy_slug,
        price_adjustment="none",
        builder_version=CONTINUOUS_BUILDER_VERSION,
        roll_schedule_version=schedule.version,
        roll_schedule_fingerprint=roll_manifest.source_fingerprint,
        contract_dataset_refs=contract_refs,
        start_session=start_session,
        end_session=end_session,
        rebuild_window_sessions=request.rebuild_window_sessions,
        source_fingerprint=source_fingerprint,
        created_at_utc=utc_clock.now(),
    )
    write_dataset_continuous_manifest(request.storage_root, dataset_ref, manifest)

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
            validation_status=ValidationStatus.PASSED,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=record_count,
            checksum=existing_metadata.checksum,
            created_at=existing_metadata.created_at,
            lineage={
                "roll_schedule_version": str(schedule.version),
                "roll_schedule_fingerprint": roll_manifest.source_fingerprint,
                "continuous_manifest_fingerprint": source_fingerprint,
            },
        )
    )

    return MaterializeContinuousTradesResult(
        dataset_ref=dataset_ref,
        manifest=manifest,
        sessions_materialized=sessions,
        record_count=record_count,
        reused=False,
    )
