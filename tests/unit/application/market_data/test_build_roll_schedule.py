"""Build roll schedule workflow tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.market_data.build_roll_schedule import (
    BuildRollScheduleRequest,
    build_roll_schedule,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.roll_schedule_manifest_store import (
    read_roll_schedule_manifest,
)
from trading_framework.infrastructure.storage.roll_schedule_repository import RollScheduleRepository
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketTrade, TradeSide
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
    return ContractTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(size),
            event_at=datetime(
                session_date.year,
                session_date.month,
                session_date.day,
                hour_utc,
                30,
                tzinfo=UTC,
            ),
            side=TradeSide.BUY,
        ),
        actual_contract=contract,
        product="NQ",
        session_date=session_date,
        source_file="sample.dbn.zst",
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


def test_build_roll_schedule_persists_schedule_and_manifest(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    contract_repo = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    nqz5_ref = _dataset_ref("NQZ5")

    start_at = datetime(2025, 7, 13, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 14, 16, 0, tzinfo=UTC)
    _register_working_metadata(registry, nqu5_ref, start_at=start_at, end_at=end_at)
    _register_working_metadata(registry, nqz5_ref, start_at=start_at, end_at=end_at)

    contract_repo.write_records(
        nqu5_ref,
        [
            _rth_record(contract="NQU5", session_date=date(2025, 7, 13), hour_utc=14, size=100),
            _rth_record(contract="NQU5", session_date=date(2025, 7, 14), hour_utc=14, size=50),
        ],
    )
    contract_repo.write_records(
        nqz5_ref,
        [
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 13), hour_utc=14, size=10),
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 14), hour_utc=14, size=200),
        ],
    )

    result = build_roll_schedule(
        BuildRollScheduleRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
            confirmation_sessions=1,
        ),
        registry=registry,
        clock=FixedClock(datetime(2025, 7, 14, 20, 0, tzinfo=UTC)),
    )

    assert result.schedule.version == 1
    assert len(result.schedule.entries) >= 1
    manifest_path = result.version_dir / "manifest.json"
    assert manifest_path.exists()
    loaded_manifest = read_roll_schedule_manifest(manifest_path)
    assert loaded_manifest.product == "NQ"
    assert loaded_manifest.policy_slug == "volume-rth-close"

    loaded_schedule, _ = RollScheduleRepository(storage_root).read(
        product="NQ",
        policy_slug="volume-rth-close",
        version=1,
        policy=result.schedule.policy,
    )
    assert loaded_schedule.entries == result.schedule.entries


def test_build_roll_schedule_requires_rth_volumes(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    contract_repo = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    start_at = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 13, 23, 0, tzinfo=UTC)
    _register_working_metadata(registry, nqu5_ref, start_at=start_at, end_at=end_at)
    contract_repo.write_records(
        nqu5_ref,
        [
            ContractTradeRecord(
                trade=MarketTrade(
                    price=Price(Decimal("1")),
                    size=Volume(1),
                    event_at=start_at,
                    side=TradeSide.BUY,
                ),
                actual_contract="NQU5",
                product="NQ",
                session_date=date(2025, 7, 13),
                source_file="overnight.dbn.zst",
            )
        ],
    )

    with pytest.raises(ValidationError, match="no RTH session volumes"):
        build_roll_schedule(
            BuildRollScheduleRequest(
                storage_root=storage_root,
                product="NQ",
                contract_dataset_refs=(nqu5_ref,),
            ),
            registry=registry,
        )
