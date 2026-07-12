"""AnalysisDataView contract tests."""

import inspect
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.data.view import AnalysisDataView, DataColumn


def _bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000 + minute),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_from_bars_builds_float64_columns_in_time_order() -> None:
    view = AnalysisDataView.from_bars([_bar(2), _bar(0), _bar(1)])
    assert len(view) == 3
    assert view.close.dtype == "float64"
    assert view.close.values == (103.0, 103.0, 103.0)
    assert view.volume.values == (1000.0, 1001.0, 1002.0)
    assert view.timestamps[0].minute == 0


def test_column_accessor_returns_named_ohlcv_fields() -> None:
    view = AnalysisDataView.from_bars([_bar(0)])
    assert view.column("HIGH").values == (105.0,)


def test_rejects_empty_bars() -> None:
    with pytest.raises(ValidationError, match="bars must be non-empty"):
        AnalysisDataView.from_bars([])


def test_rejects_mismatched_column_lengths() -> None:
    with pytest.raises(ValidationError, match="same length"):
        AnalysisDataView(
            timestamps=(datetime(2024, 1, 1, tzinfo=UTC),),
            open=DataColumn((1.0,)),
            high=DataColumn((1.0,)),
            low=DataColumn((1.0,)),
            close=DataColumn((1.0, 2.0)),
            volume=DataColumn((1.0,)),
        )


def test_view_exposes_no_mutation_api() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(AnalysisDataView)
        if inspect.isfunction(member) and not name.startswith("_")
    }
    assert public_methods <= {"from_bars", "column"}
