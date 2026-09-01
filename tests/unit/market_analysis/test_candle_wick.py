"""Tests for the causal, bar-local Candle Wick kernel and component."""

from datetime import UTC, datetime
from decimal import Decimal

import numpy as np

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import AnalysisContext, OutputId, TimeRange
from trading_framework.market_analysis.adapters.numpy.candle_wick import candle_wick
from trading_framework.market_analysis.components.candle import (
    CandleWickComponent,
    NumpyCandleWickImplementation,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspace
from trading_framework.time.models.timeframe import Timeframe


def test_candle_wick_kernel_computes_ratios_of_own_bar_range() -> None:
    open_ = np.array([10.0])
    high = np.array([20.0])
    low = np.array([0.0])
    close = np.array([15.0])

    arrays = candle_wick(open_, high, low, close)

    # range = 20, upper wick = 20 - max(10, 15) = 5 -> 5/20 = 0.25
    assert arrays.upper_wick_ratio[0] == 0.25
    # lower wick = min(10, 15) - 0 = 10 -> 10/20 = 0.5
    assert arrays.lower_wick_ratio[0] == 0.5
    # body = |15 - 10| = 5 -> 5/20 = 0.25
    assert arrays.body_ratio[0] == 0.25


def test_candle_wick_kernel_zero_range_bar_is_defined_not_nan() -> None:
    open_ = np.array([5.0])
    high = np.array([5.0])
    low = np.array([5.0])
    close = np.array([5.0])

    arrays = candle_wick(open_, high, low, close)

    assert not np.isnan(arrays.upper_wick_ratio[0])
    assert not np.isnan(arrays.lower_wick_ratio[0])
    assert not np.isnan(arrays.body_ratio[0])
    assert arrays.upper_wick_ratio[0] == 0.0
    assert arrays.lower_wick_ratio[0] == 0.0
    assert arrays.body_ratio[0] == 0.0


def test_candle_wick_kernel_is_causal_per_bar() -> None:
    # Bar 1's ratios must not depend on bar 0's or bar 2's OHLC at all.
    open_ = np.array([10.0, 50.0, 1.0])
    high = np.array([20.0, 60.0, 100.0])
    low = np.array([0.0, 40.0, 0.5])
    close = np.array([15.0, 55.0, 90.0])

    arrays = candle_wick(open_, high, low, close)
    isolated = candle_wick(open_[1:2], high[1:2], low[1:2], close[1:2])

    assert arrays.upper_wick_ratio[1] == isolated.upper_wick_ratio[0]
    assert arrays.lower_wick_ratio[1] == isolated.lower_wick_ratio[0]
    assert arrays.body_ratio[1] == isolated.body_ratio[0]


def test_candle_wick_component_declares_shape() -> None:
    component = CandleWickComponent()
    assert component.component_id.value == "candle.wick"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    assert component.parameter_schema.fields == ()
    empty_params = component.parameter_schema.canonicalize({})
    assert component.history_requirement(empty_params).bars_before == 0
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"upper_wick_ratio", "lower_wick_ratio", "body_ratio"}


def _bars() -> list[MarketBar]:
    stamps = [
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 31, tzinfo=UTC),
    ]
    ohlc = [
        (10.0, 20.0, 0.0, 15.0),
        (5.0, 5.0, 5.0, 5.0),
    ]
    bars: list[MarketBar] = []
    for observed, (open_, high, low, close) in zip(stamps, ohlc, strict=True):
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=observed,
                available_at=observed.replace(minute=observed.minute + 1),
            )
        )
    return bars


def _context() -> AnalysisContext:
    start = datetime(2024, 6, 3, 13, 30, tzinfo=UTC)
    end = datetime(2024, 6, 3, 13, 32, tzinfo=UTC)
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="candle-wick",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def test_candle_wick_implementation_zero_range_bar_is_defined() -> None:
    view = AnalysisDataView.from_bars(_bars())
    workspace = AnalysisWorkspace(view)
    implementation = NumpyCandleWickImplementation()
    parameters = CandleWickComponent().parameter_schema.canonicalize({})

    result = implementation.compute(_context(), workspace.view_for(()), parameters)

    upper = result.outputs[OutputId("upper_wick_ratio")].values
    lower = result.outputs[OutputId("lower_wick_ratio")].values
    body = result.outputs[OutputId("body_ratio")].values
    assert not any(np.isnan(upper))
    assert not any(np.isnan(lower))
    assert not any(np.isnan(body))
    assert upper[1] == 0.0
    assert lower[1] == 0.0
    assert body[1] == 0.0
    assert result.warmup.warmup_bars == 0
    assert result.validity.valid_from_index == 0
