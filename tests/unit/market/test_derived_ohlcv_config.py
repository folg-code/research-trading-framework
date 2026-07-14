"""Derived OHLCV from trades config tests."""

import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.derivation import (
    DERIVED_OHLCV_PROVIDER,
    TRADES_TO_BARS_DERIVATION_METHOD,
    TRADES_TO_BARS_VERSION,
    DerivedOhlcvFromTradesConfig,
)
from trading_framework.time.models.timeframe import Timeframe


def _trades_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="trades",
            timeframe=Timeframe("tick"),
            provider="databento",
            source_id="nq_cme_trades_2025",
        ),
        version=1,
    )


def test_derived_ohlcv_config_holds_source_and_target_identity() -> None:
    source_ref = _trades_ref()
    target_id = DatasetId(
        instrument_id=Identifier("nq"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider=DERIVED_OHLCV_PROVIDER,
        source_id="nq_1m_from_trades_2025",
    )
    config = DerivedOhlcvFromTradesConfig(
        source_dataset_ref=source_ref,
        target_dataset_id=target_id,
        schema_version="market-bar-v1",
    )

    assert config.source_dataset_ref == source_ref
    assert config.target_dataset_id.provider == DERIVED_OHLCV_PROVIDER
    assert config.normalization_version == TRADES_TO_BARS_VERSION


def test_derived_ohlcv_config_lineage_points_to_source_trades() -> None:
    source_ref = _trades_ref()
    config = DerivedOhlcvFromTradesConfig(
        source_dataset_ref=source_ref,
        target_dataset_id=DatasetId(
            instrument_id=Identifier("nq"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id="nq_1m_from_trades_2025",
        ),
        schema_version="market-bar-v1",
    )

    lineage = config.lineage()

    assert lineage["source_dataset_ref"] == str(source_ref)
    assert lineage["source_data_type"] == "trades"
    assert lineage["derivation_method"] == TRADES_TO_BARS_DERIVATION_METHOD
    assert lineage["derivation_version"] == TRADES_TO_BARS_VERSION
    assert lineage["target_timeframe"] == "1m"


def test_derived_ohlcv_config_rejects_non_trades_source() -> None:
    with pytest.raises(Exception, match="source dataset data_type must be trades"):
        DerivedOhlcvFromTradesConfig(
            source_dataset_ref=DatasetRef(
                dataset_id=DatasetId(
                    instrument_id=Identifier("nq"),
                    data_type="ohlcv",
                    timeframe=Timeframe("1m"),
                    provider="csv",
                    source_id="nq_csv",
                ),
                version=1,
            ),
            target_dataset_id=DatasetId(
                instrument_id=Identifier("nq"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider=DERIVED_OHLCV_PROVIDER,
                source_id="nq_1m_from_trades_2025",
            ),
            schema_version="market-bar-v1",
        )


def test_derived_ohlcv_config_rejects_unsupported_target_timeframe() -> None:
    with pytest.raises(Exception, match="Sprint 012 MVP supports target timeframe 1m only"):
        DerivedOhlcvFromTradesConfig(
            source_dataset_ref=_trades_ref(),
            target_dataset_id=DatasetId(
                instrument_id=Identifier("nq"),
                data_type="ohlcv",
                timeframe=Timeframe("5m"),
                provider=DERIVED_OHLCV_PROVIDER,
                source_id="nq_5m_from_trades_2025",
            ),
            schema_version="market-bar-v1",
            target_timeframe=Timeframe("5m"),
        )
