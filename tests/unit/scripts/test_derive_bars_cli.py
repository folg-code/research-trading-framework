"""CLI tests for derive_bars_from_trades script."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.market_data import derive_bars_from_trades

from tests.fixtures.databento import build_mock_dbn_store
from tests.fixtures.market import synthetic_trade_row_specs_across_minutes
from trading_framework.application.market_data import (
    finalize_dataset,
    import_databento_trades_archive,
    publish_dataset,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

_IMPORTED_AT = datetime(2025, 7, 13, 22, 0, tzinfo=UTC)
_PUBLISHED_AT = datetime(2025, 7, 14, 8, 0, tzinfo=UTC)


def _seed_published_trades(tmp_path: Path) -> tuple[Path, str]:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"mocked-dbn-archive")
    mock_store = build_mock_dbn_store(specs=synthetic_trade_row_specs_across_minutes())

    with (
        patch(
            "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
            return_value=mock_store,
        ),
        patch(
            "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
            return_value=mock_store,
        ),
    ):
        import_result = import_databento_trades_archive(
            DatabentoTradesArchiveImportConfig(
                path=archive_path,
                dataset_id=DatasetId(
                    instrument_id=Identifier("nq"),
                    data_type="trades",
                    timeframe=Timeframe("tick"),
                    provider="databento",
                    source_id="cli-source-trades",
                ),
                symbol_mapping=SymbolMapping(
                    provider_symbol="NQ.FUT",
                    instrument_id=Identifier("nq"),
                ),
                schema_version="market-trade-v1",
                normalization_version="databento-trades-v1",
            ),
            storage_root=storage_root,
            registry=registry,
            clock=FixedClock(_IMPORTED_AT),
        )

    finalize_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
    )
    publish_dataset(
        import_result.dataset_ref,
        storage_root=storage_root,
        registry=registry,
        clock=FixedClock(_PUBLISHED_AT),
    )
    return storage_root, str(import_result.dataset_ref)


def test_derive_bars_cli_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    storage_root, source_dataset_ref = _seed_published_trades(tmp_path)

    exit_code = derive_bars_from_trades.main(
        [
            "--storage-root",
            str(storage_root),
            "--source-dataset-ref",
            source_dataset_ref,
            "--instrument-id",
            "nq",
            "--derived-source-id",
            "cli-derived-1m",
            "--json",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"validation_passed": true' in output
    assert '"bar_count": 2' in output
    assert '"derivation_method": "trades_to_bars"' in output
