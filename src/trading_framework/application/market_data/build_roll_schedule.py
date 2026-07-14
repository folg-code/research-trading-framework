"""Build and persist a volume-based roll schedule from contract trade datasets."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.observability.memory_stats import process_rss_mb
from trading_framework.infrastructure.observability.profile_context import active_phase_timer
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.paths import list_contract_session_dates
from trading_framework.infrastructure.storage.roll_schedule_manifest_store import (
    ROLL_SCHEDULE_MANIFEST_VERSION,
    RollScheduleManifest,
)
from trading_framework.infrastructure.storage.roll_schedule_repository import (
    RollScheduleRepository,
    allocate_roll_schedule_version,
    compute_roll_schedule_source_fingerprint,
)
from trading_framework.market.continuous import (
    ROLL_SCHEDULE_BUILDER_VERSION,
    ROLL_SCHEDULE_SCHEMA_VERSION,
    VolumeRthCloseRollPolicy,
    aggregate_rth_session_volumes,
    build_volume_rth_close_schedule,
)
from trading_framework.market.continuous.schedule import RollSchedule
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.repositories import HistoricalTradeQuery
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _optional_phase(name: str) -> AbstractContextManager[None]:
    timer = active_phase_timer()
    if timer is None:
        return nullcontext()
    return timer.phase(name)


@dataclass(frozen=True, slots=True)
class BuildRollScheduleRequest:
    """Input for building one roll schedule version."""

    storage_root: Path
    product: str
    contract_dataset_refs: tuple[DatasetRef, ...]
    start_session: date | None = None
    end_session: date | None = None
    confirmation_sessions: int = 1
    version: int | None = None


@dataclass(frozen=True, slots=True)
class BuildRollScheduleResult:
    """Outcome of one roll schedule build."""

    schedule: RollSchedule
    manifest: RollScheduleManifest
    version_dir: Path


def _contract_code_from_dataset_ref(dataset_ref: DatasetRef) -> str:
    instrument = dataset_ref.dataset_id.instrument_id.value
    if "." not in instrument:
        msg = f"contract dataset instrument must be PRODUCT.CONTRACT, got {instrument!r}"
        raise ValidationError(msg)
    return instrument.split(".", 1)[1]


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
        msg = "no contract session_date partitions found for roll schedule build"
        raise ValidationError(msg)
    resolved_start = start_session or min(session_dates)
    resolved_end = end_session or max(session_dates)
    if resolved_end < resolved_start:
        msg = "end_session must not be before start_session"
        raise ValidationError(msg)
    return resolved_start, resolved_end


def _load_contract_records(
    storage_root: Path,
    contract_dataset_refs: tuple[DatasetRef, ...],
    *,
    start_session: date,
    end_session: date,
    registry: FileDatasetRegistry,
) -> dict[str, list[ContractTradeRecord]]:
    timer = active_phase_timer()
    repository = ParquetContractTradeDatasetRepository(storage_root)
    records_by_contract: dict[str, list[ContractTradeRecord]] = {}
    for index, dataset_ref in enumerate(contract_dataset_refs, start=1):
        metadata = registry.get(dataset_ref)
        contract_code = _contract_code_from_dataset_ref(dataset_ref)
        phase_name = f"roll_schedule.load.{contract_code}"
        if timer is not None:
            with timer.phase(phase_name):
                records = list(
                    repository.query_records(
                        HistoricalTradeQuery(
                            dataset_ref=dataset_ref,
                            start_at=metadata.start_at,
                            end_at=metadata.end_at,
                        )
                    )
                )
        else:
            records = list(
                repository.query_records(
                    HistoricalTradeQuery(
                        dataset_ref=dataset_ref,
                        start_at=metadata.start_at,
                        end_at=metadata.end_at,
                    )
                )
            )
        filtered = [
            record for record in records if start_session <= record.session_date <= end_session
        ]
        records_by_contract[contract_code] = filtered
        if timer is not None:
            rss_mb = process_rss_mb()
            rss_text = f" rss_mb={rss_mb:.1f}" if rss_mb is not None else ""
            timer.log(
                f"[{index}/{len(contract_dataset_refs)}] roll_schedule loaded {contract_code} "
                f"rows={len(filtered)}{rss_text}"
            )
    return records_by_contract


def build_roll_schedule(
    request: BuildRollScheduleRequest,
    *,
    registry: FileDatasetRegistry | None = None,
    repository: RollScheduleRepository | None = None,
    clock: Clock | None = None,
    session_resolver: CmeEsRthSessionResolver | None = None,
) -> BuildRollScheduleResult:
    """Aggregate contract RTH volumes and persist a versioned roll schedule."""
    if not request.contract_dataset_refs:
        msg = "contract_dataset_refs must not be empty"
        raise ValidationError(msg)

    dataset_registry = registry or FileDatasetRegistry(request.storage_root)
    roll_repository = repository or RollScheduleRepository(request.storage_root)
    utc_clock = clock or SystemClock()
    resolver = session_resolver or CmeEsRthSessionResolver()

    with _optional_phase("roll_schedule.session_bounds"):
        start_session, end_session = _session_bounds(
            request.storage_root,
            request.contract_dataset_refs,
            start_session=request.start_session,
            end_session=request.end_session,
        )
    policy = VolumeRthCloseRollPolicy(
        product=request.product,
        confirmation_sessions=request.confirmation_sessions,
    )
    with _optional_phase("roll_schedule.load_contract_records"):
        records_by_contract = _load_contract_records(
            request.storage_root,
            request.contract_dataset_refs,
            start_session=start_session,
            end_session=end_session,
            registry=dataset_registry,
        )
    with _optional_phase("roll_schedule.aggregate_volumes"):
        session_volumes = aggregate_rth_session_volumes(
            records_by_contract,
            resolver=resolver,
        )
    if not session_volumes:
        msg = "no RTH session volumes found for roll schedule build"
        raise ValidationError(msg)

    with _optional_phase("roll_schedule.build_entries"):
        entries = build_volume_rth_close_schedule(session_volumes, policy=policy)
    if not entries:
        msg = "roll schedule builder produced no entries"
        raise ValidationError(msg)

    version = request.version or allocate_roll_schedule_version(
        request.storage_root,
        product=policy.product,
        policy_slug=policy.slug,
    )
    schedule = RollSchedule(
        product=policy.product,
        policy=policy,
        version=version,
        entries=entries,
    )
    contract_refs = tuple(str(dataset_ref) for dataset_ref in request.contract_dataset_refs)
    manifest = RollScheduleManifest(
        manifest_version=ROLL_SCHEDULE_MANIFEST_VERSION,
        product=policy.product,
        policy_slug=policy.slug,
        schema_version=ROLL_SCHEDULE_SCHEMA_VERSION,
        builder_version=ROLL_SCHEDULE_BUILDER_VERSION,
        version=version,
        start_session=start_session,
        end_session=end_session,
        confirmation_sessions=policy.confirmation_sessions,
        contract_dataset_refs=contract_refs,
        source_fingerprint=compute_roll_schedule_source_fingerprint(
            contract_dataset_refs=contract_refs,
            start_session=start_session,
            end_session=end_session,
            policy=policy,
        ),
        created_at_utc=utc_clock.now(),
    )
    with _optional_phase("roll_schedule.persist"):
        version_dir = roll_repository.write(schedule, manifest=manifest)
    return BuildRollScheduleResult(
        schedule=schedule,
        manifest=manifest,
        version_dir=version_dir,
    )
