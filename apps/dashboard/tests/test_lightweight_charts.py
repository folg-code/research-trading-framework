"""Tests for Lightweight Charts OHLCV helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from dashboard_app.charts.lightweight import (
    candles_from_ohlcv_bars,
    candles_from_status_bars,
    markers_for_fills,
    markers_for_trade,
    to_unix_seconds,
)
from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, TradeView
from dashboard_app.query.service import OhlcvBarRow


def test_candles_from_ohlcv_bars_are_sorted_and_unique() -> None:
    bars = (
        OhlcvBarRow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            observed_at_utc=datetime(2026, 7, 18, 12, 1, tzinfo=UTC),
            open=1,
            high=2,
            low=0.5,
            close=1.5,
            volume=10,
        ),
        OhlcvBarRow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            observed_at_utc=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
            open=1,
            high=2,
            low=0.5,
            close=1.2,
            volume=10,
        ),
        OhlcvBarRow(
            schema_version=PRESENTATION_SCHEMA_VERSION,
            observed_at_utc=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
            open=9,
            high=9,
            low=9,
            close=9,
            volume=1,
        ),
    )
    candles = candles_from_ohlcv_bars(bars)
    assert [c.time for c in candles] == [
        to_unix_seconds(datetime(2026, 7, 18, 12, 0, tzinfo=UTC)),
        to_unix_seconds(datetime(2026, 7, 18, 12, 1, tzinfo=UTC)),
    ]
    assert candles[0].close == 1.2


def test_markers_for_trade_long_entry_exit() -> None:
    trade = TradeView(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        trade_id="t1",
        side="long",
        entry_at_utc=datetime(2026, 7, 18, 12, 0, tzinfo=UTC),
        exit_at_utc=datetime(2026, 7, 18, 12, 5, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
    )
    markers = markers_for_trade(trade)
    assert [m.text for m in markers] == ["long entry", "exit"]
    assert markers[0].shape == "arrowUp"
    assert markers[1].shape == "arrowDown"


def test_status_bars_and_fill_markers() -> None:
    candles = candles_from_status_bars(
        [
            {
                "observed_at": "2026-07-18T12:00:00+00:00",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
            }
        ]
    )
    assert len(candles) == 1
    markers = markers_for_fills(
        [{"filled_at": "2026-07-18T12:00:00+00:00", "price": 100.5, "side": "buy"}]
    )
    assert markers[0].text == "buy"
    assert markers[0].shape == "circle"
