"""Tests for the portfolio demo index generator."""

from __future__ import annotations

from pathlib import Path

from scripts.demo.run_portfolio_demo import (
    _LIVE_DRY_RUN_DASHBOARD_NAME,
    DemoArtifact,
    _write_index_html,
)


def test_write_index_html_highlights_live_demo_and_existing_reports(tmp_path: Path) -> None:
    (tmp_path / _LIVE_DRY_RUN_DASHBOARD_NAME).write_text("<html></html>", encoding="utf-8")
    (tmp_path / "07_robustness_dashboard.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "market_and_signal.html").write_text("<html></html>", encoding="utf-8")
    live_url = "https://dryrun.example.com"

    index_path = _write_index_html(
        output_dir=tmp_path,
        artifacts=[
            DemoArtifact(
                filename=_LIVE_DRY_RUN_DASHBOARD_NAME,
                title="Live Dry Run",
                workflow="AWS -> status",
                description="Live worker status.",
                status="ok",
            ),
            DemoArtifact(
                filename="01_strategy_dashboard_fixture.html",
                title="Fixture Strategy Dashboard",
                workflow="Fixture OHLCV -> simulation",
                description="Small deterministic strategy report.",
                status="skipped",
            ),
        ],
        live_demo_url=live_url,
    )

    html = index_path.read_text(encoding="utf-8")

    assert "Trading Research Framework Portfolio" in html
    assert "BTCUSDT execution demo on AWS" in html
    assert live_url in html
    assert "Open static fallback" in html
    assert "Data foundation" in html
    assert "Research engine" in html
    assert "Strategy and execution" in html
    assert "Robustness Research Dashboard" in html
    assert "Market And Signal Drill-Down" in html
    assert "workflow labels show how" in html
    assert "the framework produced them" in html
