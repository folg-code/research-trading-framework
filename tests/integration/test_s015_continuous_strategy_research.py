"""Integration tests for continuous futures strategy research read path."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from trading_framework.application.market_data.build_continuous import (
    BuildContinuousRequest,
    build_continuous,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_BUILD_AT = datetime(2025, 7, 15, 20, 0, tzinfo=UTC)


def _dataset_ref(contract: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(f"NQ.{contract}"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-s015-e2e",
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
    return ContractTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(size),
            event_at=datetime(
                session_date.year,
                session_date.month,
                session_date.day,
                14,
                minute,
                tzinfo=UTC,
            ),
            side=TradeSide.BUY,
        ),
        actual_contract=contract,
        product="NQ",
        session_date=session_date,
        source_file="sample.dbn.zst",
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


def test_run_strategy_research_reads_published_continuous_ohlcv(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    nqu5_ref, nqz5_ref = _seed_contract_datasets(storage_root)
    build_result = build_continuous(
        BuildContinuousRequest(
            storage_root=storage_root,
            product="NQ",
            contract_dataset_refs=(nqu5_ref, nqz5_ref),
        ),
        clock=FixedClock(_BUILD_AT),
    )
    metadata = FileDatasetRegistry(storage_root).get(build_result.continuous_ohlcv_dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED

    result = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=build_result.continuous_ohlcv_dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=build_canonical_strategy_model(),
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    )

    assert result.run_id == result.manifest.run_id
    assert len(result.equity) > 0
