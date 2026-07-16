"""Tests for the portfolio live dry-run status page generator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.demo.run_portfolio_demo import (
    _LIVE_DRY_RUN_DASHBOARD_NAME,
    _LIVE_DRY_RUN_FIXTURE_NAME,
    _build_live_dry_run_dashboard,
)


def test_build_live_dry_run_dashboard_writes_static_page_and_fixture(tmp_path: Path) -> None:
    status_url = "https://example.execute-api.eu-north-1.amazonaws.com/status"

    artifact = _build_live_dry_run_dashboard(output_dir=tmp_path, status_url=status_url)

    assert artifact.filename == _LIVE_DRY_RUN_DASHBOARD_NAME
    assert artifact.status == "ok"

    fixture = json.loads((tmp_path / _LIVE_DRY_RUN_FIXTURE_NAME).read_text(encoding="utf-8"))
    assert fixture["runtime_id"] == "btc-futures-dry-run-aws"
    assert fixture["simulated"] is True
    assert fixture["price_history"]
    assert fixture["equity_history"]
    assert fixture["recent_fills"][0]["side"] == "buy"

    html = (tmp_path / _LIVE_DRY_RUN_DASHBOARD_NAME).read_text(encoding="utf-8")
    assert status_url in html
    assert "lightweight-charts" in html
    assert "BTCUSDT price with simulated fill markers" in html
    assert "Paper equity" in html
    assert "Last Simulated Trades" in html
    assert "priceSeries.setMarkers" in html
    assert "equitySeries.setData" in html
    assert "All orders, fills, positions and PnL" in html
    assert "are simulated." in html
    assert "No exchange account, API keys or real capital are connected." in html
    assert "Status endpoint unavailable" in html
    assert "staleAfterSeconds" in html
