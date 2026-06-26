"""Tests for NumPy market analysis adapters."""

from datetime import UTC, datetime

import numpy as np
import pytest

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis.adapters.numpy.kernels import atr_sma, true_range
from trading_framework.market_analysis.adapters.numpy.result_builder import (
    build_analysis_result,
    ndarray_to_output_series,
)
from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.outputs import (
    OutputFieldSpec,
    OutputGroup,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


def test_true_range_kernel_matches_wilder_definition() -> None:
    high = np.array([105.0, 108.0, 110.0], dtype=np.float64)
    low = np.array([95.0, 101.0, 104.0], dtype=np.float64)
    close = np.array([102.0, 107.0, 105.0], dtype=np.float64)
    values = true_range(high, low, close)
    assert values[0] == pytest.approx(10.0)
    assert values[1] == pytest.approx(7.0)
    assert values[2] == pytest.approx(6.0)


def test_atr_kernel_uses_simple_moving_average() -> None:
    tr = np.array([10.0, 7.0, 6.0, 5.0], dtype=np.float64)
    values = atr_sma(tr, 3)
    assert np.isnan(values[0])
    assert np.isnan(values[1])
    assert values[2] == pytest.approx((10.0 + 7.0 + 6.0) / 3.0)


def test_ndarray_to_output_series_converts_float64_values() -> None:
    series = ndarray_to_output_series(np.array([1.0, 2.5], dtype=np.float64))
    assert series.dtype == "float64"
    assert series.values == (1.0, 2.5)


def test_build_analysis_result_populates_identity_and_validity() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    context = AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1h"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )
    schema = OutputSchema(
        outputs=(
            OutputFieldSpec(
                output_id=OutputId("value"),
                dtype="float64",
                group=OutputGroup.CORE,
            ),
        )
    )
    parameters = CanonicalParameters.from_mapping({})
    result = build_analysis_result(
        context=context,
        component_id=ComponentId("volatility.true_range"),
        component_version=ComponentVersion("1.0.0"),
        implementation_id=ImplementationId("numpy.true_range"),
        implementation_version=ImplementationVersion("1.0.0"),
        parameters=parameters,
        dependency_keys=(),
        output_schema=schema,
        outputs={
            OutputId("value"): ndarray_to_output_series(np.array([1.0, 2.0], dtype=np.float64))
        },
        warmup_bars=0,
        valid_from_index=0,
        bar_count=2,
    )
    assert result.computation_identity.component_id == ComponentId("volatility.true_range")
    assert result.validity.valid_from_index == 0
    assert result.validity.valid_to_index == 1
