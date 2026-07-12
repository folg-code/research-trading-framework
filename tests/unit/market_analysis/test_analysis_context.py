"""Analysis context tests."""

from datetime import UTC, datetime

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import AnalysisContext, TimeRange
from trading_framework.time.models.timeframe import Timeframe


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample",
        ),
        version=1,
    )


def test_analysis_context_requires_matching_timeframe() -> None:
    requested = TimeRange(
        start=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 15, 0, tzinfo=UTC),
    )
    wider = TimeRange(
        start=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        end=datetime(2024, 1, 1, 16, 0, tzinfo=UTC),
    )
    context = AnalysisContext(
        dataset_ref=_dataset_ref(),
        timeframe=Timeframe("1m"),
        requested_range=requested,
        computation_range=wider,
        engine_version="0.1.0",
    )
    assert context.requested_range == requested


def test_analysis_context_rejects_mismatched_timeframe() -> None:
    time_range = TimeRange(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 2, tzinfo=UTC),
    )
    with pytest.raises(ValidationError, match="timeframe"):
        AnalysisContext(
            dataset_ref=_dataset_ref(),
            timeframe=Timeframe("5m"),
            requested_range=time_range,
            computation_range=time_range,
            engine_version="0.1.0",
        )
