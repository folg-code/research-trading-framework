"""Databento OHLCV archive import config tests."""

from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers import (
    DatabentoOhlcvArchiveImportConfig,
    SymbolMapping,
)
from trading_framework.time.models.timeframe import Timeframe


def test_ohlcv_archive_import_config_holds_dataset_identity() -> None:
    dataset_id = DatasetId(
        instrument_id=Identifier("nq"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="databento",
        source_id="nq_cme_ohlcv_1m_2025",
    )
    config = DatabentoOhlcvArchiveImportConfig(
        path=Path("user_data/sample.dbn.zst"),
        dataset_id=dataset_id,
        symbol_mapping=SymbolMapping(
            provider_symbol="NQ.FUT",
            instrument_id=Identifier("nq"),
        ),
        schema_version="market-bar-v1",
        normalization_version="databento-ohlcv-1m-v1",
    )

    assert config.dataset_id.data_type == "ohlcv"
    assert config.dataset_id.timeframe == Timeframe("1m")
    assert config.symbol_mapping.provider_symbol == "NQ.FUT"
