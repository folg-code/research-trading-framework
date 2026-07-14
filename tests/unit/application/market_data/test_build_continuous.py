"""Build continuous workflow tests."""

from datetime import UTC, date, datetime
from pathlib import Path

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.application.market_data.build_continuous import (
    BuildContinuousRequest,
    build_continuous,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.paths import dataset_metadata_path
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

_BUILD_AT = datetime(2025, 7, 15, 20, 0, tzinfo=UTC)


def _dataset_ref(contract: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(f"NQ.{contract}"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-20250714",
        ),
        version=1,
    )


def _rth_record(
    *,
    contract: str,
    session_date: date,
    minute: int,
    size: int,
) -> ContractTradeRecord:
    return make_rth_contract_trade_record(
        contract=contract,
        session_date=session_date,
        minute=minute,
        size=size,
    )


def _seed_contract_datasets(storage_root: Path) -> tuple[DatasetRef, DatasetRef]:
    registry = FileDatasetRegistry(storage_root)
    contract_repo = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    nqz5_ref = _dataset_ref("NQZ5")
    start_at = datetime(2025, 7, 14, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 15, 15, 0, tzinfo=UTC)
    for dataset_ref in (nqu5_ref, nqz5_ref):
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
                schema_version="market-trade-contract-v2",
                normalization_version="databento-contract-trades-v1",
                validation_status=ValidationStatus.PASSED,
                lifecycle_status=DatasetLifecycleState.WORKING,
                row_count=1,
                checksum="abc",
                created_at=start_at,
                lineage={},
            )
        )
    contract_repo.write_records(
        nqu5_ref,
        [
            _rth_record(contract="NQU5", session_date=date(2025, 7, 14), minute=0, size=100),
            _rth_record(contract="NQU5", session_date=date(2025, 7, 14), minute=1, size=10),
            _rth_record(contract="NQU5", session_date=date(2025, 7, 15), minute=0, size=50),
        ],
    )
    contract_repo.write_records(
        nqz5_ref,
        [
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 14), minute=0, size=10),
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 15), minute=0, size=200),
            _rth_record(contract="NQZ5", session_date=date(2025, 7, 15), minute=1, size=20),
        ],
    )
    return nqu5_ref, nqz5_ref


def test_build_continuous_publishes_trades_and_ohlcv(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_datasets(storage_root)
    registry = FileDatasetRegistry(storage_root)
    clock = FixedClock(_BUILD_AT)

    result = build_continuous(
        BuildContinuousRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        registry=registry,
        clock=clock,
    )

    trades_metadata = registry.get(result.continuous_trades_dataset_ref)
    ohlcv_metadata = registry.get(result.continuous_ohlcv_dataset_ref)

    assert result.trades_reused is False
    assert result.ohlcv_reused is False
    assert result.published_trades is True
    assert result.published_ohlcv is True
    assert trades_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert ohlcv_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert str(result.continuous_ohlcv_dataset_ref).startswith(
        "NQ.c.0|ohlcv|1m|derived|volume-rth-close@"
    )


def test_build_continuous_reuses_unchanged_outputs(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_datasets(storage_root)
    registry = FileDatasetRegistry(storage_root)
    clock = FixedClock(_BUILD_AT)
    request = BuildContinuousRequest(
        storage_root=storage_root,
        product="NQ",
        contract_dataset_refs=(nqu5_ref, nqz5_ref),
    )

    first = build_continuous(request, registry=registry, clock=clock)
    second = build_continuous(request, registry=registry, clock=clock)

    assert second.trades_reused is True
    assert second.ohlcv_reused is True
    assert second.continuous_trades_dataset_ref == first.continuous_trades_dataset_ref
    assert second.continuous_ohlcv_dataset_ref == first.continuous_ohlcv_dataset_ref
    assert second.published_trades is False
    assert second.published_ohlcv is False


def test_build_continuous_derives_ohlcv_when_trades_reused_but_ohlcv_missing(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_datasets(storage_root)
    registry = FileDatasetRegistry(storage_root)
    clock = FixedClock(_BUILD_AT)
    request = BuildContinuousRequest(
        storage_root=storage_root,
        product="NQ",
        contract_dataset_refs=(nqu5_ref, nqz5_ref),
    )

    first = build_continuous(request, registry=registry, clock=clock)
    ohlcv_metadata_path = dataset_metadata_path(storage_root, first.continuous_ohlcv_dataset_ref)
    ohlcv_metadata_path.unlink()

    second = build_continuous(request, registry=registry, clock=clock)

    assert second.trades_reused is True
    assert second.ohlcv_reused is False
    assert second.published_ohlcv is True
    assert second.continuous_trades_dataset_ref == first.continuous_trades_dataset_ref
    assert registry.get(second.continuous_ohlcv_dataset_ref).lifecycle_status is (
        DatasetLifecycleState.PUBLISHED
    )
