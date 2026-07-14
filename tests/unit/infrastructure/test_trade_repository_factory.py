"""Trade repository factory routing tests."""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.application.market_data.finalize_dataset import finalize_dataset
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.continuous_trade_repository import (
    ParquetContinuousTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_query_adapter import (
    ContractTradeQueryAdapter,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_repository import (
    ParquetContractTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.parquet.trade_repository import (
    ParquetTradeDatasetRepository,
)
from trading_framework.infrastructure.storage.trade_repository_factory import (
    trade_dataset_repository_for,
)
from trading_framework.market.continuous.identity import (
    CONTINUOUS_TRADES_PROVIDER,
    continuous_instrument_id,
)
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketTrade, TradeSide
from trading_framework.market.repositories import HistoricalTradeQuery, TradeDatasetRepository
from trading_framework.time.models.timeframe import Timeframe


def _contract_dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.NQU5"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-test",
        ),
        version=1,
    )


def test_trade_repository_factory_routes_contract_datasets(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    dataset_ref = _contract_dataset_ref()

    repository = trade_dataset_repository_for(storage_root, dataset_ref)

    assert isinstance(repository, ContractTradeQueryAdapter)


def test_trade_repository_factory_routes_legacy_datasets(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    dataset_ref = DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="legacy",
        ),
        version=1,
    )

    repository = trade_dataset_repository_for(storage_root, dataset_ref)

    assert isinstance(repository, ParquetTradeDatasetRepository)


def test_finalize_contract_trades_dataset(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetContractTradeDatasetRepository(storage_root)
    dataset_ref = _contract_dataset_ref()
    start_at = datetime(2025, 7, 14, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 14, 15, 0, tzinfo=UTC)
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
            checksum="pending",
            created_at=start_at,
            lineage={},
        )
    )
    repository.write_session_partition(
        dataset_ref,
        date(2025, 7, 14),
        [make_rth_contract_trade_record(contract="NQU5", session_date=date(2025, 7, 14))],
        merge_existing=False,
    )

    finalized_ref = finalize_dataset(dataset_ref, storage_root=storage_root, registry=registry)
    metadata = registry.get(finalized_ref)

    assert metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert metadata.row_count == 1


def _continuous_dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=continuous_instrument_id("NQ"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider=CONTINUOUS_TRADES_PROVIDER,
            source_id="volume-rth-close",
        ),
        version=1,
    )


def _continuous_trade_record(session_date: date) -> ContinuousTradeRecord:
    event_at = datetime(2025, 7, 14, 14, 30, tzinfo=UTC)
    return ContinuousTradeRecord(
        trade=MarketTrade(
            price=Price(Decimal("22860.75")),
            size=Volume(2),
            event_at=event_at,
            side=TradeSide.BUY,
            received_at=event_at,
            trade_id="t1",
            sequence=1,
        ),
        actual_contract="NQU5",
        product="NQ",
        session_date=session_date,
        continuous_symbol="NQ_CONT",
        roll_id="roll-1",
        is_roll_boundary=False,
    )


class _QueryTradesMustNotBeCalled(TradeDatasetRepository):
    def query_trades(self, query: HistoricalTradeQuery) -> list[MarketTrade]:
        msg = "query_trades must not be called for partitioned trades finalize"
        raise AssertionError(msg)

    def write_trades(
        self,
        dataset_ref: DatasetRef,
        trades: Sequence[MarketTrade],
    ) -> None:
        msg = "write_trades must not be called in this test"
        raise AssertionError(msg)


def test_finalize_continuous_trades_dataset(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetContinuousTradeDatasetRepository(storage_root)
    dataset_ref = _continuous_dataset_ref()
    start_at = datetime(2025, 7, 14, 14, 0, tzinfo=UTC)
    end_at = datetime(2025, 7, 14, 15, 0, tzinfo=UTC)
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
            schema_version="market-trade-continuous-v1",
            normalization_version="continuous-trades-v1",
            validation_status=ValidationStatus.PASSED,
            lifecycle_status=DatasetLifecycleState.WORKING,
            row_count=1,
            checksum="pending",
            created_at=start_at,
            lineage={},
        )
    )
    repository.write_session_records(
        dataset_ref,
        date(2025, 7, 14),
        [_continuous_trade_record(date(2025, 7, 14))],
    )

    finalized_ref = finalize_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=registry,
        trade_repository=_QueryTradesMustNotBeCalled(),
    )
    metadata = registry.get(finalized_ref)

    assert metadata.lifecycle_status is DatasetLifecycleState.FINALIZED
    assert metadata.row_count == 1
