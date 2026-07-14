"""Tests for columnar OHLCV loading and simulation compile."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import polars as pl

from trading_framework.application.market_data.ohlcv_columnar import ohlcv_column_batch_from_table
from trading_framework.application.market_data.query_historical import query_historical_columnar
from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet import ParquetDatasetRepository
from trading_framework.infrastructure.storage.parquet.writer import market_bars_to_table
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.research.simulation.compile import (
    compile_simulation_input,
    compile_simulation_input_from_columnar,
)
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="columnar",
        ),
        version=1,
    )


def _bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100.5")),
        high=Price(Decimal("105.25")),
        low=Price(Decimal("99.75")),
        close=Price(Decimal("103.125")),
        volume=Volume(1000 + minute),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_column_batch_matches_market_bars_materialization(tmp_path: Path) -> None:
    bars = [_bar(0), _bar(1), _bar(2)]
    table = market_bars_to_table(bars)
    column_batch = ohlcv_column_batch_from_table(table)
    view = column_batch.to_analysis_view()

    assert view.timestamps == tuple(bar.observed_at for bar in bars)
    assert view.close.values == (103.125, 103.125, 103.125)
    assert AnalysisDataView.from_bars(bars).close.values == view.close.values


def _published_metadata(dataset_ref: DatasetRef) -> DatasetMetadata:
    start_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 12, 2, tzinfo=UTC)
    return DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=Identifier("NQ.c.0"),
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="columnar",
        data_type="ohlcv",
        start_at=start_at,
        end_at=end_at,
        schema_version="ohlcv.v1",
        normalization_version="utc-interval-start.v1",
        validation_status=ValidationStatus.PASSED,
        lifecycle_status=DatasetLifecycleState.PUBLISHED,
        row_count=3,
        checksum="abc123",
        created_at=start_at,
        published_at=datetime(2024, 6, 2, tzinfo=UTC),
    )


def test_query_historical_columnar_matches_query_bars(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)
    dataset_ref = _dataset_ref()
    registry.register(
        replace(
            _published_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.WORKING,
            published_at=None,
        )
    )
    registry.update(
        replace(
            _published_metadata(dataset_ref),
            lifecycle_status=DatasetLifecycleState.FINALIZED,
            published_at=None,
        )
    )
    registry.update(_published_metadata(dataset_ref))
    bars = [_bar(0), _bar(1), _bar(2)]
    repository.write_bars(dataset_ref, bars)

    from trading_framework.application.market_data.query_historical import (
        QueryHistoricalRequest,
        query_historical,
    )

    request = QueryHistoricalRequest(
        dataset_ref=dataset_ref,
        start_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        end_at=datetime(2024, 1, 1, 12, 2, tzinfo=UTC),
    )
    loaded_bars = query_historical(
        request,
        storage_root=storage_root,
        registry=registry,
        repository=repository,
    )
    column_batch = query_historical_columnar(
        request,
        storage_root=storage_root,
        registry=registry,
        repository=repository,
    )

    assert column_batch.timestamps == tuple(bar.observed_at for bar in loaded_bars)
    assert column_batch.close == tuple(float(bar.close.value) for bar in loaded_bars)


def test_compile_simulation_input_from_columnar_matches_bars() -> None:
    bars = [_bar(0), _bar(1)]
    table = market_bars_to_table(bars)
    column_batch = ohlcv_column_batch_from_table(table)
    entry_signals = pl.DataFrame(
        {
            "available_at": [bars[1].available_at],
            "direction": ["long"],
        }
    )

    from_bars = compile_simulation_input(bars=bars, entry_signals=entry_signals)
    from_columnar = compile_simulation_input_from_columnar(
        column_batch=column_batch,
        entry_signals=entry_signals,
    )

    assert from_bars.bars.observed_at_ns.tolist() == from_columnar.bars.observed_at_ns.tolist()
    assert from_bars.bars.close_prices.tolist() == from_columnar.bars.close_prices.tolist()
