"""Derive continuous OHLCV workflow tests."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.application.market_data.build_roll_schedule import (
    BuildRollScheduleRequest,
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
from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
from trading_framework.application.market_data.query_trades import QueryTradesRequest, query_trades
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.continuous_ohlcv_manifest_store import (
    read_continuous_ohlcv_manifest,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.paths import (
    continuous_ohlcv_manifest_path,
    list_ohlcv_session_dates,
)
from trading_framework.market.continuous.identity import CONTINUOUS_TRADES_PROVIDER
from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    TRADES_TO_BARS_DERIVATION_METHOD,
    TRADES_TO_BARS_VERSION,
    DerivedContinuousOhlcvConfig,
    roll_schedule_ref,
)
from trading_framework.market.repositories import HistoricalBarQuery
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_PUBLISHED_AT = datetime(2025, 7, 15, 20, 0, tzinfo=UTC)
_DERIVED_AT = datetime(2025, 7, 15, 21, 0, tzinfo=UTC)


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


def _publish_continuous_pipeline(tmp_path: Path) -> tuple[Path, FileDatasetRegistry, DatasetRef]:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    contract_repo = ParquetContractTradeDatasetRepository(storage_root)
    nqu5_ref = _dataset_ref("NQU5")
    nqz5_ref = _dataset_ref("NQZ5")
    start_at = datetime(2025, 7, 14, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 15, 15, 0, tzinfo=UTC)
    _register_working_metadata(registry, nqu5_ref, start_at=start_at, end_at=end_at)
    _register_working_metadata(registry, nqz5_ref, start_at=start_at, end_at=end_at)
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
    clock = FixedClock(_PUBLISHED_AT)
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
    materialized = materialize_continuous_trades(
        MaterializeContinuousTradesRequest(
            storage_root=storage_root,
            product="NQ",
            roll_schedule_version=1,
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        registry=registry,
        clock=clock,
    )
    finalize_dataset(
        materialized.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        materialized.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=clock,
    )
    return storage_root, registry, materialized.dataset_ref


def _derive_config(source_ref: DatasetRef) -> DerivedContinuousOhlcvConfig:
    return DerivedContinuousOhlcvConfig(
        source_continuous_trades_ref=source_ref,
        target_dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id=VOLUME_RTH_CLOSE_POLICY_SLUG,
        ),
        schema_version="market-bar-v1",
    )


def test_derive_continuous_ohlcv_registers_working_dataset_with_roll_lineage(
    tmp_path: Path,
) -> None:
    storage_root, registry, source_ref = _publish_continuous_pipeline(tmp_path)
    bar_repository = ParquetDatasetRepository(storage_root)

    result = derive_continuous_ohlcv(
        _derive_config(source_ref),
        storage_root=storage_root,
        registry=registry,
        bar_repository=bar_repository,
        clock=FixedClock(_DERIVED_AT),
    )

    metadata = registry.get(result.dataset_ref)
    lineage = metadata.lineage or {}

    assert result.validation_result.is_valid is True
    assert result.bar_count >= 1
    assert result.source_dataset_ref == source_ref
    assert result.roll_schedule_version == 1
    assert metadata.lifecycle_status is DatasetLifecycleState.WORKING
    assert metadata.provider == DERIVED_OHLCV_PROVIDER
    assert lineage["continuous_trades_dataset_ref"] == str(source_ref)
    assert lineage["roll_schedule_ref"] == roll_schedule_ref(
        product="NQ",
        policy_slug=VOLUME_RTH_CLOSE_POLICY_SLUG,
        version=1,
    )
    assert lineage["derivation_method"] == TRADES_TO_BARS_DERIVATION_METHOD
    assert lineage["derivation_version"] == TRADES_TO_BARS_VERSION
    assert "continuous_ohlcv_manifest_fingerprint" in lineage
    assert list_ohlcv_session_dates(storage_root, result.dataset_ref)
    assert continuous_ohlcv_manifest_path(storage_root, result.dataset_ref).exists()
    manifest = read_continuous_ohlcv_manifest(
        continuous_ohlcv_manifest_path(storage_root, result.dataset_ref)
    )
    assert manifest.source_continuous_trades_ref == str(source_ref)
    assert manifest.source_continuous_manifest_fingerprint


def test_derive_continuous_ohlcv_rejects_unpublished_source(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    source_ref = DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider=CONTINUOUS_TRADES_PROVIDER,
            source_id=VOLUME_RTH_CLOSE_POLICY_SLUG,
        ),
        version=1,
    )
    registry.register(
        DatasetMetadata(
            dataset_ref=source_ref,
            instrument_id=source_ref.dataset_id.instrument_id,
            timeframe=source_ref.dataset_id.timeframe,
            provider=source_ref.dataset_id.provider,
            source_id=source_ref.dataset_id.source_id,
            data_type=source_ref.dataset_id.data_type,
            start_at=_PUBLISHED_AT,
            end_at=_PUBLISHED_AT,
            schema_version="market-trade-continuous-v1",
            normalization_version="continuous-trades-builder-v1",
            validation_status=ValidationStatus.PASSED,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=0,
            checksum="pending",
            created_at=_PUBLISHED_AT,
            lineage={},
        )
    )

    with pytest.raises(Exception, match="source continuous trades dataset must be published"):
        derive_continuous_ohlcv(
            _derive_config(source_ref),
            storage_root=storage_root,
            registry=registry,
            clock=FixedClock(_DERIVED_AT),
        )


def test_query_trades_and_historical_read_published_continuous_datasets(tmp_path: Path) -> None:
    storage_root, registry, trades_ref = _publish_continuous_pipeline(tmp_path)
    derive_result = derive_continuous_ohlcv(
        _derive_config(trades_ref),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
    )
    finalize_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        derive_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
    )

    trades_metadata = registry.get(trades_ref)
    trades = query_trades(
        QueryTradesRequest(
            dataset_ref=trades_ref,
            start_at=trades_metadata.start_at,
            end_at=trades_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )
    assert len(trades) >= 2
    assert all(trade.event_at.tzinfo is not None for trade in trades)

    bars_metadata = registry.get(derive_result.dataset_ref)
    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=derive_result.dataset_ref,
            start_at=bars_metadata.start_at,
            end_at=bars_metadata.end_at,
        ),
        storage_root=storage_root,
        registry=registry,
    )
    assert len(bars) >= 1

    stored = ParquetDatasetRepository(storage_root).query_bars(
        HistoricalBarQuery(
            dataset_ref=derive_result.dataset_ref,
            start_at=bars_metadata.start_at,
            end_at=bars_metadata.end_at,
        )
    )
    assert len(stored) == len(bars)


def test_derive_continuous_ohlcv_reuses_matching_manifest(tmp_path: Path) -> None:
    storage_root, registry, source_ref = _publish_continuous_pipeline(tmp_path)

    first = derive_continuous_ohlcv(
        _derive_config(source_ref),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
    )
    second = derive_continuous_ohlcv(
        _derive_config(source_ref),
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_DERIVED_AT),
        existing_dataset_ref=first.dataset_ref,
    )

    assert second.reused is True
    assert second.dataset_ref == first.dataset_ref
    assert second.sessions_derived == ()
