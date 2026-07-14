"""CLI tests for build_continuous script."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from scripts.market_data import build_continuous as build_continuous_cli

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.core.identifiers import Identifier
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
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref(contract: str) -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier(f"NQ.{contract}"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq-cme-trades-cli",
        ),
        version=1,
    )


def _seed_contract_datasets(storage_root: Path) -> tuple[str, str]:
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

    def _record(contract: str, session_date: date, minute: int, size: int) -> ContractTradeRecord:
        return make_rth_contract_trade_record(
            contract=contract,
            session_date=session_date,
            minute=minute,
            size=size,
        )

    contract_repo.write_records(
        nqu5_ref,
        [
            _record("NQU5", date(2025, 7, 14), 0, 100),
            _record("NQU5", date(2025, 7, 15), 0, 50),
        ],
    )
    contract_repo.write_records(
        nqz5_ref,
        [
            _record("NQZ5", date(2025, 7, 14), 0, 10),
            _record("NQZ5", date(2025, 7, 15), 0, 200),
        ],
    )
    return str(nqu5_ref), str(nqz5_ref)


def test_build_continuous_cli_json_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    storage_root = tmp_path / "data"
    nqu5_ref, nqz5_ref = _seed_contract_datasets(storage_root)

    exit_code = build_continuous_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--product",
            "NQ",
            "--contract-dataset-ref",
            nqu5_ref,
            "--contract-dataset-ref",
            nqz5_ref,
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "continuous_ohlcv_dataset_ref" in captured.out
    assert "NQ.c.0|ohlcv|1m|derived|volume-rth-close@" in captured.out
