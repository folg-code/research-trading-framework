"""Tests for the VPS-hosted live dry-run dashboard server."""

from __future__ import annotations

from pathlib import Path

from scripts.portfolio_live.serve_live_dry_run_dashboard import (
    LiveDashboardConfig,
    _load_history,
    _public_config,
    _store_status_snapshot,
    create_app,
    render_dashboard_html,
)


def test_render_dashboard_html_contains_live_chart_contract() -> None:
    html = render_dashboard_html(
        LiveDashboardConfig(
            status_url="https://example.execute-api.eu-north-1.amazonaws.com/status",
            poll_seconds=5,
            candle_seconds=60,
        )
    )

    assert "BTC Futures Dry-Run Live" in html
    assert "addCandlestickSeries" in html
    assert "equityChart.addLineSeries" in html
    assert "fetch('/api/status'" in html
    assert "fetch('/api/history'" in html
    assert "upsertCandle" not in html
    assert "setInterval(refresh, config.pollSeconds * 1000)" in html
    assert "All orders, fills, positions and PnL" in html


def test_public_config_does_not_expose_status_url() -> None:
    config = LiveDashboardConfig(
        status_url="https://example.execute-api.eu-north-1.amazonaws.com/status",
        poll_seconds=7,
        candle_seconds=30,
        stale_after_seconds=90,
    )

    payload = _public_config(config)

    assert payload == {
        "pollSeconds": 7,
        "candleSeconds": 30,
        "staleAfterSeconds": 90,
        "historyHours": 24,
        "source": "aws-status-api",
    }


def test_create_app_registers_vps_routes() -> None:
    app = create_app(LiveDashboardConfig(status_url="", use_fixture=True))

    routes = {
        (route.method, route.resource.canonical)
        for route in app.router.routes()
        if route.resource is not None
    }

    assert ("GET", "/") in routes
    assert ("GET", "/api/config") in routes
    assert ("GET", "/api/status") in routes
    assert ("GET", "/api/history") in routes
    assert ("GET", "/health") in routes


def test_store_status_snapshot_persists_recent_bars_equity_and_fills(tmp_path: Path) -> None:
    config = LiveDashboardConfig(status_url="", use_fixture=True, db_path=tmp_path / "history.db")
    app = create_app(config)
    assert app is not None

    _store_status_snapshot(
        config,
        {
            "generated_at": "2026-07-16T12:00:30+00:00",
            "paper_equity": "10005",
            "recent_bars": [
                {
                    "observed_at": "2026-07-16T12:00:00+00:00",
                    "available_at": "2026-07-16T12:01:00+00:00",
                    "open": "65000",
                    "high": "65020",
                    "low": "64990",
                    "close": "65010",
                    "volume": 100,
                }
            ],
            "recent_fills": [
                {
                    "fill_id": "fill-1",
                    "order_id": "order-1",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "quantity": "0.001",
                    "price": "65010",
                    "filled_at": "2026-07-16T12:00:10+00:00",
                }
            ],
        },
    )

    history = _load_history(config)

    assert history["bars"][0]["close"] == 65010
    assert history["equity"][0]["equity"] == 10005
    assert history["fills"][0]["fill_id"] == "fill-1"
