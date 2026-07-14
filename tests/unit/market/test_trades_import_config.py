"""Databento trades archive import config tests."""

from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import DatabentoTradesArchiveImportConfig, SymbolMapping
from trading_framework.time.models.timeframe import Timeframe


def test_trades_archive_import_config_holds_dataset_identity() -> None:
    dataset_id = DatasetId(
        instrument_id=Identifier("nq"),
        data_type="trades",
        timeframe=Timeframe("tick"),
        provider="databento",
        source_id="nq_cme_trades_2025",
    )
    config = DatabentoTradesArchiveImportConfig(
        path=Path("user_data/sample.dbn.zst"),
        dataset_id=dataset_id,
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-trade-v1",
        normalization_version="databento-trades-v1",
    )

    assert config.dataset_id.data_type == "trades"
    assert config.symbol_mapping.provider_symbol == "NQ.FUT"
