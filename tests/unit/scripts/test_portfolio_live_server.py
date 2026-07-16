"""Tests for the VPS-hosted live dry-run dashboard server."""

from __future__ import annotations

from scripts.portfolio_live.serve_live_dry_run_dashboard import (
    LiveDashboardConfig,
    _public_config,
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
    assert ("GET", "/health") in routes
