"""Materialize continuous trades workflow tests."""

from datetime import UTC, date, datetime
from pathlib import Path

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.application.market_data.build_roll_schedule import (
    BuildRollScheduleRequest,
    build_roll_schedule,
)
from trading_framework.application.market_data.finalize_dataset import finalize_dataset
from trading_framework.application.market_data.materialize_continuous_trades import (
    MaterializeContinuousTradesRequest,
    materialize_continuous_trades,
)
from trading_framework.application.market_data.publish_dataset import publish_dataset
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.continuous_manifest_store import (
    read_continuous_trades_manifest,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.paths import continuous_trades_manifest_path
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref(contract: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(f"NQ.{contract}"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-20250713",
        ),
        version=1,
    )


def _rth_record(
    *,
    contract: str,
    session_date: date,
    hour_utc: int,
    size: int,
) -> ContractTradeRecord:
    return make_rth_contract_trade_record(
        contract=contract,
        session_date=session_date,
        hour_utc=hour_utc,
        size=size,
    )


def _register_working_metadata(
    registry: FileDatasetRegistry,
    dataset_ref: DatasetRef,
    *,
    start_at: datetime,
    end_at: datetime,
) -> None:
    registry.register(
        DatasetMetadata(
            dataset_ref=dataset_ref,
            instrument_id=dataset_ref.dataset_id.instrument_id,
            timeframe=dataset_ref.dataset_id.timeframe,
            provider=dataset_ref.dataset_id.provider,
            source_id=dataset_ref.dataset_id.source_id,
            data_type=dataset_ref.dataset_id.data_type,
            start_at=start_at,
            end_at=end_at,
            schema_version="market-trade-contract-v1",
            normalization_version="databento-contract-trades-v1",
            validation_status=ValidationStatus.PASSED,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=1,
            checksum="abc",
            created_at=start_at,
            lineage={},
        )
    )


def _seed_contract_data(storage_root: Path) -> tuple[DatasetRef, DatasetRef]:
    registry = FileDatasetRegistry(storage_root)
    contract_repo = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    nqz5_ref = _dataset_ref("NQZ5")
    start_at = datetime(2025, 7, 14, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 15, 16, 0, tzinfo=UTC)
    _register_working_metadata(registry, nqu5_ref, start_at=start_at, end_at=end_at)
    _register_working_metadata(registry, nqz5_ref, start_at=start_at, end_at=end_at)
    contract_repo.write_records(
        nqu5_ref,
        [
            _rth_record(contract="NQU5", session_date=date(2025, 7, 14), hour_utc=14, size=100),
            _rth_record(contract="NQU5", session_date=date(2025, 7, 15), hour_utc=14, size=50),
        ],
    )
    contract_repo.write_records(
        nqz5_ref,
        [
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 14), hour_utc=14, size=10),
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 15), hour_utc=14, size=200),
        ],
    )
    return nqu5_ref, nqz5_ref


def test_materialize_continuous_trades_persists_manifest_and_partitions(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_data(storage_root)
    clock = FixedClock(datetime(2025, 7, 15, 20, 0, tzinfo=UTC))
    registry = FileDatasetRegistry(storage_root)

    roll_result = build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            confirmation_sessions=1,
        ),
        registry=registry,
        clock=clock,
    )

    result = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=roll_result.schedule.version,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        registry=registry,
        clock=clock,
    )

    assert result.reused is False
    assert result.record_count == 2
    assert str(result.dataset_ref).startswith("NQ.c.0|trades|tick|continuous|volume-rth-close@")
    manifest_path = continuous_trades_manifest_path(storage_root, result.dataset_ref)
    assert manifest_path.exists()
    manifest = read_continuous_trades_manifest(manifest_path)
    assert manifest.roll_schedule_version == 1
    assert manifest.source_fingerprint == result.manifest.source_fingerprint

    continuous_repo = ParquetContinuousTradeDatasetRepository(storage_root)
    july_15 = continuous_repo.read_session_records(result.dataset_ref, date(2025, 7, 15))
    assert len(july_15) == 1
    assert july_15[0].actual_contract == "NQZ5"
    assert july_15[0].is_roll_boundary is True


def test_materialize_continuous_trades_parallel_workers_match_sequential(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_data(storage_root)
    clock = FixedClock(datetime(2025, 7, 15, 20, 0, tzinfo=UTC))
    registry = FileDatasetRegistry(storage_root)

    roll_result = build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            confirmation_sessions=1,
        ),
        registry=registry,
        clock=clock,
    )

    sequential = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=roll_result.schedule.version,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            session_workers=1,
            reuse_if_unchanged=False,
            rebuild_all=True,
        ),
        registry=registry,
        clock=clock,
    )
    parallel = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=roll_result.schedule.version,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            existing_dataset_ref=sequential.dataset_ref,
            session_workers=2,
            reuse_if_unchanged=False,
            rebuild_all=True,
        ),
        registry=registry,
        clock=clock,
    )

    assert parallel.record_count == sequential.record_count
    continuous_repo = ParquetContinuousTradeDatasetRepository(storage_root)
    sequential_rows = continuous_repo.read_session_records(
        sequential.dataset_ref, date(2025, 7, 15)
    )
    parallel_rows = continuous_repo.read_session_records(parallel.dataset_ref, date(2025, 7, 15))
    assert [row.actual_contract for row in parallel_rows] == [
        row.actual_contract for row in sequential_rows
    ]


def test_materialize_continuous_trades_reuses_unchanged_fingerprint(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_data(storage_root)
    clock = FixedClock(datetime(2025, 7, 15, 20, 0, tzinfo=UTC))
    registry = FileDatasetRegistry(storage_root)

    build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            confirmation_sessions=1,
        ),
        registry=registry,
        clock=clock,
    )

    first = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=1,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        registry=registry,
        clock=clock,
    )
    second = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=1,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            existing_dataset_ref=first.dataset_ref,
        ),
        registry=registry,
        clock=clock,
    )

    assert second.reused is True
    assert second.dataset_ref == first.dataset_ref
    assert second.sessions_materialized == ()


def test_materialize_continuous_trades_allocates_new_version_when_published(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_data(storage_root)
    clock = FixedClock(datetime(2025, 7, 15, 20, 0, tzinfo=UTC))
    registry = FileDatasetRegistry(storage_root)

    build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            confirmation_sessions=1,
        ),
        registry=registry,
        clock=clock,
    )

    first = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=1,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        registry=registry,
        clock=clock,
    )
    finalize_dataset(first.dataset_ref, storage_root=storage_root, registry=registry)
    publish_dataset(first.dataset_ref, storage_root=storage_root, registry=registry, clock=clock)

    second = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=1,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            existing_dataset_ref=first.dataset_ref,
            rebuild_all=True,
        ),
        registry=registry,
        clock=clock,
    )

    assert second.reused is False
    assert second.dataset_ref.version == first.dataset_ref.version + 1
    assert registry.get(second.dataset_ref).lifecycle_status is DatasetLifecycleState.WORKING
