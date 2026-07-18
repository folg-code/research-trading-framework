"""Generate offline HTML portfolio demos: workflows + dashboards.

Fast path (~30s): fixture OHLCV → strategy dashboard + Plotly inspection reports.
Full path (+~15s): reuse or refresh NQ half-year strategy dashboard when storage exists.

Run:

    uv run python scripts/demo/run_portfolio_demo.py
    uv run python scripts/demo/run_portfolio_demo.py --full --open

Plotly reports require: ``uv pip install plotly``
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading_framework.market.datasets import DatasetRef

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_OHLCV_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "market_data" / "ohlcv_sample_1m.csv"

_DEFAULT_OUTPUT = _REPO_ROOT / "artifacts" / "demo" / "output"
_DEFAULT_HALF_YEAR_STORAGE = _REPO_ROOT / "user_data"
_HALF_YEAR_DASHBOARD_NAME = "00_strategy_dashboard_nq_half_year.html"
_FIXTURE_DASHBOARD_NAME = "01_strategy_dashboard_fixture.html"
_LIVE_DRY_RUN_DASHBOARD_NAME = "09_live_dry_run_status.html"
_LIVE_DRY_RUN_FIXTURE_NAME = "live_dry_run_status_fixture.json"
_PUBLIC_LIVE_DEMO_URL = "https://dryrun.filipf.online"


@dataclass(frozen=True, slots=True)
class DemoArtifact:
    """One generated HTML artifact shown on the portfolio index."""

    filename: str
    title: str
    workflow: str
    description: str
    status: str  # ok | skipped | failed


_KNOWN_PORTFOLIO_ARTIFACTS: tuple[DemoArtifact, ...] = (
    DemoArtifact(
        filename=_HALF_YEAR_DASHBOARD_NAME,
        title="NQ Half-Year Strategy Dashboard",
        workflow="Published OHLCV -> Strategy Model -> Simulation -> Dashboard",
        description=(
            "Full-depth strategy research report with KPIs, equity curve, trade markers "
            "and embedded 1m source bars."
        ),
        status="ok",
    ),
    DemoArtifact(
        filename="market_and_signal.html",
        title="Market And Signal Drill-Down",
        workflow="AnalysisFrame -> Market Model x Signal Model -> Outcome Window",
        description=(
            "Readable inspection view for one market-and-signal occurrence, including "
            "context, outcome horizon and chart evidence."
        ),
        status="ok",
    ),
    DemoArtifact(
        filename="07_robustness_dashboard.html",
        title="Robustness Research Dashboard",
        workflow="Experiment Spec -> Child Strategy Runs -> Robustness Verdict",
        description=(
            "Parameter sweeps, walk-forward checks, stress tests and Monte Carlo evidence "
            "for strategy fragility review."
        ),
        status="ok",
    ),
    DemoArtifact(
        filename="08_model_research_nq_half_year.html",
        title="Model Research Methodology",
        workflow="Signal Definition Spec -> Bounded Run -> Analytics -> Report Index",
        description=(
            "Methodology-first report index for signal/model research scopes, quality flags "
            "and forward outcome analysis."
        ),
        status="ok",
    ),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build offline HTML portfolio demos (workflows + dashboards).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Directory for HTML artifacts (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include NQ half-year strategy dashboard when user_data storage exists",
    )
    parser.add_argument(
        "--half-year-storage",
        type=Path,
        default=_DEFAULT_HALF_YEAR_STORAGE,
        help="Storage root with published continuous NQ OHLCV and optional strategy runs",
    )
    parser.add_argument(
        "--refresh-half-year",
        action="store_true",
        help="Re-run half-year strategy research before rendering (requires --full)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the portfolio index in the default browser",
    )
    parser.add_argument(
        "--skip-plotly",
        action="store_true",
        help="Skip Plotly-based inspection reports",
    )
    parser.add_argument(
        "--live-status-url",
        default="",
        help="Public read-only AWS dry-run status endpoint used by the live dashboard page",
    )
    parser.add_argument(
        "--live-demo-url",
        default=_PUBLIC_LIVE_DEMO_URL,
        help="Public VPS live dashboard URL highlighted on the portfolio index",
    )
    return parser


def _plotly_available() -> bool:
    return importlib.util.find_spec("plotly") is not None


def _run_subprocess(
    *,
    label: str,
    argv: list[str],
) -> tuple[bool, str]:
    print(f"[demo] {label}...", flush=True)
    completed = subprocess.run(
        argv,
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        return False, stderr.splitlines()[-1] if stderr else f"exit code {completed.returncode}"
    return True, "ok"


def _write_published_fixture_dataset(storage_root: Path) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.core.identifiers import Identifier
    from trading_framework.market.datasets import DatasetId
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics
    from trading_framework.time.models.timeframe import Timeframe

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="portfolio-demo-fixture",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=_OHLCV_FIXTURE,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    return result.dataset_ref


def _build_fixture_strategy_dashboard(
    *,
    workspace: Path,
    output_path: Path,
) -> DemoArtifact:
    from scripts.strategy_research import render_strategy_dashboard as render_dashboard_cli
    from trading_framework.application.strategy_research import (
        RunStrategyResearchRequest,
        run_strategy_research,
    )
    from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
    from trading_framework.market_analysis.models.time_range import TimeRange
    from trading_framework.research.simulation import SimulationAssumptions
    from trading_framework.strategy import build_canonical_strategy_model
    from trading_framework.time.models.timeframe import Timeframe
    from trading_framework.time.sessions import CmeEsRthSessionResolver

    print("[demo] fixture strategy research + dashboard...", flush=True)
    storage_root = workspace / "fixture_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    dataset_ref = _write_published_fixture_dataset(storage_root)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    research = run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=build_canonical_strategy_model(),
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
            persist=True,
        )
    )
    exit_code = render_dashboard_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--run-id",
            research.run_id,
            "--output",
            str(output_path),
        ]
    )
    if exit_code != 0:
        return DemoArtifact(
            filename=_FIXTURE_DASHBOARD_NAME,
            title="Strategy Research Dashboard (fixture)",
            workflow="Market Data → Analysis → Models → Simulation → Dashboard",
            description="Canonical strategy on committed OHLCV fixture.",
            status="failed",
        )
    return DemoArtifact(
        filename=_FIXTURE_DASHBOARD_NAME,
        title="Strategy Research Dashboard (fixture)",
        workflow="Market Data → Analysis → Models → Simulation → Dashboard",
        description=(
            f"12 KPIs, equity/drawdown panes, trade markers on OHLCV "
            f"(run_id={research.run_id}, trades={len(research.trades)})."
        ),
        status="ok",
    )


def _build_half_year_strategy_dashboard(
    *,
    storage_root: Path,
    output_path: Path,
    refresh: bool,
) -> DemoArtifact:
    from scripts.strategy_research import render_strategy_dashboard as render_dashboard_cli
    from trading_framework.infrastructure.storage.metadata.discovery import (
        latest_published_dataset_ref,
    )
    from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
    from trading_framework.market.continuous.identity import continuous_instrument_id
    from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
    from trading_framework.market.datasets import DatasetId
    from trading_framework.market.derivation import DERIVED_OHLCV_PROVIDER
    from trading_framework.time.models.timeframe import Timeframe

    if not storage_root.exists():
        return DemoArtifact(
            filename=_HALF_YEAR_DASHBOARD_NAME,
            title="Strategy Research Dashboard (NQ half-year)",
            workflow="Continuous OHLCV → Strategy Research → Dashboard",
            description=f"Storage not found: {storage_root}",
            status="skipped",
        )

    dataset_ref = latest_published_dataset_ref(
        storage_root,
        DatasetId(
            instrument_id=continuous_instrument_id("NQ"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider=DERIVED_OHLCV_PROVIDER,
            source_id=VOLUME_RTH_CLOSE_POLICY_SLUG,
        ),
    )
    if dataset_ref is None:
        return DemoArtifact(
            filename=_HALF_YEAR_DASHBOARD_NAME,
            title="Strategy Research Dashboard (NQ half-year)",
            workflow="Continuous OHLCV → Strategy Research → Dashboard",
            description="No published continuous NQ OHLCV dataset in storage.",
            status="skipped",
        )

    if refresh:
        ok, message = _run_subprocess(
            label="half-year strategy research",
            argv=[
                sys.executable,
                "scripts/market_data/run_half_year_backtest.py",
                "--storage-root",
                str(storage_root),
                "--skip-build",
            ],
        )
        if not ok:
            return DemoArtifact(
                filename=_HALF_YEAR_DASHBOARD_NAME,
                title="Strategy Research Dashboard (NQ half-year)",
                workflow="Continuous OHLCV → Strategy Research → Dashboard",
                description=message,
                status="failed",
            )

    from trading_framework.infrastructure.storage.paths import strategy_research_root

    runs_dir = strategy_research_root(storage_root) / "runs"
    run_id: str | None = None
    if runs_dir.exists():
        run_dirs = sorted(
            (path for path in runs_dir.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if run_dirs:
            run_id = run_dirs[0].name

    if run_id is None:
        return DemoArtifact(
            filename=_HALF_YEAR_DASHBOARD_NAME,
            title="Strategy Research Dashboard (NQ half-year)",
            workflow="Continuous OHLCV → Strategy Research → Dashboard",
            description="No persisted strategy run found; pass --refresh-half-year.",
            status="skipped",
        )

    exit_code = render_dashboard_cli.main(
        [
            "--storage-root",
            str(storage_root),
            "--run-id",
            run_id,
            "--output",
            str(output_path),
        ]
    )
    if exit_code != 0:
        return DemoArtifact(
            filename=_HALF_YEAR_DASHBOARD_NAME,
            title="Strategy Research Dashboard (NQ half-year)",
            workflow="Continuous OHLCV → Strategy Research → Dashboard",
            description=f"Dashboard render failed for run_id={run_id}.",
            status="failed",
        )
    registry = FileDatasetRegistry(storage_root)
    ohlcv_metadata = registry.get(dataset_ref)
    return DemoArtifact(
        filename=_HALF_YEAR_DASHBOARD_NAME,
        title="Strategy Research Dashboard (NQ half-year)",
        workflow="Continuous OHLCV → Strategy Research → Dashboard",
        description=(
            f"Production-scale NQ continuous 1m OHLCV "
            f"({ohlcv_metadata.row_count:,} bars, run_id={run_id})."
        ),
        status="ok",
    )


def _build_plotly_report(
    *,
    script_relpath: str,
    output_path: Path,
    extra_args: list[str],
    artifact: DemoArtifact,
    generate: bool = False,
) -> DemoArtifact:
    argv = [
        sys.executable,
        script_relpath,
        "--output",
        str(output_path),
        *extra_args,
    ]
    if generate:
        argv.insert(2, "--generate")
    ok, message = _run_subprocess(label=artifact.title, argv=argv)
    if not ok:
        return DemoArtifact(
            filename=artifact.filename,
            title=artifact.title,
            workflow=artifact.workflow,
            description=message,
            status="failed",
        )
    return DemoArtifact(
        filename=artifact.filename,
        title=artifact.title,
        workflow=artifact.workflow,
        description=artifact.description,
        status="ok",
    )


def _build_live_dry_run_dashboard(
    *,
    output_dir: Path,
    status_url: str,
) -> DemoArtifact:
    fixture_payload = _live_dry_run_fixture_payload()
    fixture_path = output_dir / _LIVE_DRY_RUN_FIXTURE_NAME
    fixture_path.write_text(
        json.dumps(fixture_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    dashboard_path = output_dir / _LIVE_DRY_RUN_DASHBOARD_NAME
    dashboard_path.write_text(
        _live_dry_run_dashboard_html(
            status_url=status_url.strip(),
            fixture_filename=_LIVE_DRY_RUN_FIXTURE_NAME,
            fixture_payload=fixture_payload,
        ),
        encoding="utf-8",
    )
    return DemoArtifact(
        filename=_LIVE_DRY_RUN_DASHBOARD_NAME,
        title="Live BTC Futures Dry-Run Status",
        workflow="AWS ECS dry-run worker -> DynamoDB -> Lambda/API Gateway -> static page",
        description=(
            "Read-only portfolio page for live BTCUSDT market status, simulated position/PnL, "
            "recent events and stale/offline states."
        ),
        status="ok",
    )


def _live_dry_run_fixture_payload() -> dict[str, object]:
    return {
        "runtime_id": "btc-futures-dry-run-aws",
        "mode": "dry_run",
        "provider": "binance_usdm",
        "symbol": "BTCUSDT",
        "status": "stopped",
        "generated_at": "2026-07-16T11:55:13.603882+00:00",
        "last_heartbeat_at": "2026-07-16T11:55:00.524881+00:00",
        "last_market_event_at": "2026-07-16T11:55:00+00:00",
        "last_price": "64173.40",
        "current_signal": "no_signal",
        "current_position": {
            "symbol": "BTCUSDT",
            "side": "flat",
            "quantity": "0",
            "average_entry_price": None,
            "mark_price": "64173.40",
            "unrealized_pnl": "0",
            "updated_at": "2026-07-16T11:55:00+00:00",
            "simulated": True,
        },
        "paper_equity": "10000",
        "realized_pnl": "0",
        "unrealized_pnl": "0",
        "price_history": [
            {"time": "2026-07-16T11:54:00+00:00", "price": "64100.20"},
            {"time": "2026-07-16T11:55:00+00:00", "price": "64173.40"},
            {"time": "2026-07-16T11:56:00+00:00", "price": "64220.10"},
            {"time": "2026-07-16T11:57:00+00:00", "price": "64188.70"},
        ],
        "recent_bars": [
            {
                "observed_at": "2026-07-16T11:54:00+00:00",
                "available_at": "2026-07-16T11:55:00+00:00",
                "open": "64080.00",
                "high": "64120.00",
                "low": "64060.00",
                "close": "64100.20",
                "volume": 128,
                "simulated": True,
            },
            {
                "observed_at": "2026-07-16T11:55:00+00:00",
                "available_at": "2026-07-16T11:56:00+00:00",
                "open": "64100.20",
                "high": "64185.00",
                "low": "64095.10",
                "close": "64173.40",
                "volume": 164,
                "simulated": True,
            },
            {
                "observed_at": "2026-07-16T11:56:00+00:00",
                "available_at": "2026-07-16T11:57:00+00:00",
                "open": "64173.40",
                "high": "64240.00",
                "low": "64160.20",
                "close": "64220.10",
                "volume": 191,
                "simulated": True,
            },
            {
                "observed_at": "2026-07-16T11:57:00+00:00",
                "available_at": "2026-07-16T11:58:00+00:00",
                "open": "64220.10",
                "high": "64225.50",
                "low": "64170.00",
                "close": "64188.70",
                "volume": 142,
                "simulated": True,
            },
        ],
        "equity_history": [
            {"time": "2026-07-16T11:54:00+00:00", "equity": "10000"},
            {"time": "2026-07-16T11:55:00+00:00", "equity": "10000"},
            {"time": "2026-07-16T11:56:00+00:00", "equity": "10002.35"},
            {"time": "2026-07-16T11:57:00+00:00", "equity": "10001.10"},
        ],
        "recent_orders": [
            {
                "order_id": "paper-order-1",
                "intent_id": "btc-dry-run-long-1",
                "strategy_id": "btc_ema_dry_run",
                "symbol": "BTCUSDT",
                "side": "buy",
                "order_type": "market",
                "quantity": "0.001",
                "status": "simulated_filled",
                "created_at": "2026-07-16T11:55:00+00:00",
                "simulated": True,
            },
            {
                "order_id": "paper-order-2",
                "intent_id": "btc-dry-run-exit-1",
                "strategy_id": "btc_ema_dry_run",
                "symbol": "BTCUSDT",
                "side": "sell",
                "order_type": "market",
                "quantity": "0.001",
                "status": "simulated_filled",
                "created_at": "2026-07-16T11:57:00+00:00",
                "simulated": True,
            },
        ],
        "recent_fills": [
            {
                "fill_id": "paper-fill-1",
                "order_id": "paper-order-1",
                "symbol": "BTCUSDT",
                "side": "buy",
                "quantity": "0.001",
                "price": "64173.40",
                "filled_at": "2026-07-16T11:55:00+00:00",
                "liquidity": "simulated",
                "simulated": True,
            },
            {
                "fill_id": "paper-fill-2",
                "order_id": "paper-order-2",
                "symbol": "BTCUSDT",
                "side": "sell",
                "quantity": "0.001",
                "price": "64188.70",
                "filled_at": "2026-07-16T11:57:00+00:00",
                "liquidity": "simulated",
                "simulated": True,
            },
        ],
        "recent_events": [
            {
                "event_id": "btc-futures-dry-run-aws-000001-runtime_started",
                "event_type": "runtime_started",
                "occurred_at": "2026-07-16T11:54:21.775065+00:00",
                "symbol": "BTCUSDT",
                "payload": {"status": "running", "simulated": "true"},
                "correlation_id": None,
                "simulated": True,
            },
            {
                "event_id": "btc-futures-dry-run-aws-000004-market_event_received",
                "event_type": "market_event_received",
                "occurred_at": "2026-07-16T11:55:00.525495+00:00",
                "symbol": "BTCUSDT",
                "payload": {"current_signal": "no_signal", "simulated": "true"},
                "correlation_id": None,
                "simulated": True,
            },
        ],
        "simulated": True,
    }


def _live_dry_run_dashboard_html(
    *,
    status_url: str,
    fixture_filename: str,
    fixture_payload: dict[str, object],
) -> str:
    config_json = json.dumps(
        {
            "statusUrl": status_url,
            "fixtureUrl": fixture_filename,
            "fixturePayload": fixture_payload,
            "pollSeconds": 30,
            "staleAfterSeconds": 180,
        },
        sort_keys=True,
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Live BTC Futures Dry-Run Status</title>
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101418;
      --band: #171d23;
      --panel: #1f2830;
      --line: #34404b;
      --text: #eef3f8;
      --muted: #aab6c2;
      --accent: #4fb06d;
      --warn: #f0b84a;
      --bad: #ef6b73;
      --blue: #64a7ff;
      --buy: #3dd68c;
      --sell: #ff6b6b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      background: var(--band);
      border-bottom: 1px solid var(--line);
      padding: 1.25rem;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 1.25rem;
    }}
    .top {{
      max-width: 1180px;
      margin: 0 auto;
      display: grid;
      gap: 0.8rem;
      grid-template-columns: 1fr auto;
      align-items: end;
    }}
    h1 {{ margin: 0; font-size: 1.55rem; letter-spacing: 0; }}
    .subtitle {{ color: var(--muted); margin: 0.25rem 0 0; }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0.4rem 0.75rem;
      color: var(--text);
      background: #11171d;
      font-weight: 700;
      white-space: nowrap;
    }}
    .pill.running {{ border-color: var(--accent); color: var(--accent); }}
    .pill.stale, .pill.stopped {{ border-color: var(--warn); color: var(--warn); }}
    .pill.offline, .pill.failed {{ border-color: var(--bad); color: var(--bad); }}
    .notice {{
      border: 1px solid #6f5f2b;
      background: #211d12;
      color: #f8df9a;
      padding: 0.9rem 1rem;
      margin-bottom: 1rem;
      border-radius: 8px;
      font-weight: 650;
    }}
    .grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(12, 1fr);
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 1rem;
    }}
    .wide {{ grid-column: span 12; }}
    .half {{ grid-column: span 6; }}
    .third {{ grid-column: span 4; }}
    h2 {{ margin: 0 0 0.8rem; font-size: 1rem; }}
    dl {{
      margin: 0;
      display: grid;
      gap: 0.65rem;
      grid-template-columns: minmax(130px, 0.8fr) minmax(0, 1.2fr);
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; font-weight: 650; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ padding: 0.55rem 0.4rem; border-bottom: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-weight: 650; }}
    .chart-grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.65fr);
    }}
    .chart-host {{
      height: 340px;
      min-height: 260px;
      width: 100%;
    }}
    .chart-small {{ height: 250px; }}
    .table-wrap {{ overflow-x: auto; }}
    .section-kicker {{
      margin: -0.35rem 0 0.8rem;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .side-buy {{ color: var(--buy); font-weight: 700; }}
    .side-sell {{ color: var(--sell); font-weight: 700; }}
    .empty {{ color: var(--muted); margin: 0; }}
    .error {{ color: var(--bad); font-weight: 650; }}
    .fresh {{ color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    code {{ color: var(--blue); }}
    @media (max-width: 820px) {{
      .top {{ grid-template-columns: 1fr; }}
      .half, .third {{ grid-column: span 12; }}
      .chart-grid {{ grid-template-columns: 1fr; }}
      dl {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="top">
      <div>
        <h1>Live BTC Futures Dry-Run Status</h1>
        <p class="subtitle">AWS-hosted read-only runtime status for the portfolio demo.</p>
      </div>
      <div id="status-pill" class="pill">LOADING</div>
    </div>
  </header>
  <main>
    <div class="notice">
      This demo uses live Binance BTCUSDT futures market data. All orders, fills, positions and PnL
      are simulated. No exchange account, API keys or real capital are connected.
    </div>
    <div id="error" class="error"></div>
    <div class="grid">
      <section class="third"><h2>Runtime</h2><dl id="runtime"></dl></section>
      <section class="third"><h2>Market</h2><dl id="market"></dl></section>
      <section class="third"><h2>Paper Account</h2><dl id="account"></dl></section>
      <section class="wide">
        <h2>Live Price, Simulated Trades And Equity</h2>
        <p class="section-kicker">
          The page keeps a rolling in-browser history from API polls; the fixture seeds the offline
          portfolio view.
        </p>
        <div class="chart-grid">
          <div>
            <div class="chart-title">BTCUSDT price with simulated fill markers</div>
            <div id="chart-price" class="chart-host"></div>
          </div>
          <div>
            <div class="chart-title">Paper equity</div>
            <div id="chart-equity" class="chart-host chart-small"></div>
          </div>
        </div>
      </section>
      <section class="half"><h2>Current Paper Position</h2><dl id="position"></dl></section>
      <section class="half">
        <h2>Last Simulated Trades</h2><div id="last-trades"></div>
      </section>
      <section class="wide"><h2>Recent Simulated Orders</h2><div id="orders"></div></section>
      <section class="wide"><h2>Recent Runtime Events</h2><div id="events"></div></section>
    </div>
  </main>
  <script id="live-config" type="application/json">{config_json}</script>
  <script>
    const config = JSON.parse(document.getElementById('live-config').textContent);
    const params = new URLSearchParams(window.location.search);
    const statusUrl = params.get('statusUrl') || config.statusUrl || '';
    const pollMs = config.pollSeconds * 1000;
    const staleAfterMs = config.staleAfterSeconds * 1000;
    const priceHistory = [];
    const equityHistory = [];
    let priceChart;
    let priceSeries;
    let equityChart;
    let equitySeries;

    function text(value) {{
      return value === null || value === undefined || value === '' ? 'n/a' : String(value);
    }}

    function setPairs(id, pairs) {{
      document.getElementById(id).innerHTML = pairs
        .map(([key, value]) => `<dt>${{key}}</dt><dd>${{text(value)}}</dd>`)
        .join('');
    }}

    function ageMs(iso) {{
      const value = Date.parse(iso || '');
      return Number.isFinite(value) ? Date.now() - value : Number.POSITIVE_INFINITY;
    }}

    function effectiveStatus(payload) {{
      if (!payload) return 'offline';
      if (ageMs(payload.last_heartbeat_at) > staleAfterMs) return 'stale';
      return String(payload.status || 'unknown').toLowerCase();
    }}

    function setStatus(payload, offlineMessage) {{
      const status = offlineMessage ? 'offline' : effectiveStatus(payload);
      const pill = document.getElementById('status-pill');
      pill.className = `pill ${{status}}`;
      pill.textContent = status.toUpperCase();
      document.getElementById('error').textContent = offlineMessage || '';
    }}

    function renderRows(items, columns) {{
      if (!items || !items.length) return '<p class="empty">No recent simulated records.</p>';
      const head = columns.map((column) => `<th>${{column.label}}</th>`).join('');
      const rows = items.map((item) => `<tr>${{
        columns.map((column) => `<td>${{formatCell(item, column)}}</td>`).join('')
      }}</tr>`).join('');
      return `<div class="table-wrap"><table><thead><tr>${{head}}</tr></thead>` +
        `<tbody>${{rows}}</tbody></table></div>`;
    }}

    function formatCell(item, column) {{
      const value = column.render ? column.render(item) : item[column.key];
      if (column.key === 'side') {{
        const side = String(value || '').toLowerCase();
        if (side === 'buy') return '<span class="side-buy">BUY</span>';
        if (side === 'sell') return '<span class="side-sell">SELL</span>';
      }}
      return text(value);
    }}

    function toUnixSeconds(iso) {{
      const value = Date.parse(iso || '');
      return Number.isFinite(value) ? Math.floor(value / 1000) : null;
    }}

    function toNumber(value) {{
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }}

    function upsertPoint(points, point) {{
      if (!point || point.time === null || point.value === null) return;
      const index = points.findIndex((item) => item.time === point.time);
      if (index >= 0) points[index] = point;
      else points.push(point);
      points.sort((left, right) => left.time - right.time);
      while (points.length > 240) points.shift();
    }}

    function seedHistory(payload) {{
      for (const row of payload.price_history || []) {{
        upsertPoint(priceHistory, {{
          time: toUnixSeconds(row.time),
          value: toNumber(row.price),
        }});
      }}
      for (const row of payload.equity_history || []) {{
        upsertPoint(equityHistory, {{
          time: toUnixSeconds(row.time),
          value: toNumber(row.equity),
        }});
      }}
    }}

    function appendLivePoints(payload) {{
      const marketTime = payload.last_market_event_at || payload.generated_at;
      upsertPoint(priceHistory, {{
        time: toUnixSeconds(marketTime),
        value: toNumber(payload.last_price),
      }});
      upsertPoint(equityHistory, {{
        time: toUnixSeconds(payload.generated_at || payload.last_heartbeat_at || marketTime),
        value: toNumber(payload.paper_equity),
      }});
    }}

    function makeChart(containerId) {{
      const container = document.getElementById(containerId);
      if (!container || !window.LightweightCharts) return null;
      return LightweightCharts.createChart(container, {{
        layout: {{ background: {{ color: '#1f2830' }}, textColor: '#eef3f8' }},
        grid: {{ vertLines: {{ color: '#2b3540' }}, horzLines: {{ color: '#2b3540' }} }},
        rightPriceScale: {{ borderColor: '#34404b' }},
        timeScale: {{ borderColor: '#34404b', timeVisible: true, secondsVisible: false }},
        crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      }});
    }}

    function ensureCharts() {{
      if (!window.LightweightCharts) {{
        document.getElementById('chart-price').innerHTML =
          '<p class="empty">Price chart unavailable because Lightweight Charts did not load.</p>';
        document.getElementById('chart-equity').innerHTML =
          '<p class="empty">Equity chart unavailable because Lightweight Charts did not load.</p>';
        return false;
      }}
      if (!priceChart) {{
        priceChart = makeChart('chart-price');
        priceSeries = priceChart.addLineSeries({{ color: '#64a7ff', lineWidth: 2 }});
      }}
      if (!equityChart) {{
        equityChart = makeChart('chart-equity');
        equitySeries = equityChart.addLineSeries({{ color: '#3dd68c', lineWidth: 2 }});
      }}
      return true;
    }}

    function renderCharts(payload) {{
      seedHistory(payload);
      appendLivePoints(payload);
      if (!ensureCharts()) return;
      priceSeries.setData(priceHistory);
      equitySeries.setData(equityHistory);
      priceSeries.setMarkers((payload.recent_fills || [])
        .map((fill) => {{
          const side = String(fill.side || '').toLowerCase();
          const price = toNumber(fill.price);
          return {{
            time: toUnixSeconds(fill.filled_at),
            position: side === 'buy' ? 'belowBar' : 'aboveBar',
            color: side === 'buy' ? '#3dd68c' : '#ff6b6b',
            shape: side === 'buy' ? 'arrowUp' : 'arrowDown',
            text: `${{side.toUpperCase()}} ${{price === null ? '' : price.toFixed(2)}}`,
          }};
        }})
        .filter((marker) => marker.time !== null));
      priceChart.timeScale().fitContent();
      equityChart.timeScale().fitContent();
    }}

    function render(payload) {{
      setStatus(payload);
      renderCharts(payload);
      const heartbeatAge = Math.round(ageMs(payload.last_heartbeat_at) / 1000);
      setPairs('runtime', [
        ['Runtime id', payload.runtime_id],
        ['Mode', payload.mode],
        ['Provider', payload.provider],
        ['Status', payload.status],
        ['Last heartbeat', payload.last_heartbeat_at],
        ['Heartbeat age', `${{heartbeatAge}}s`],
      ]);
      setPairs('market', [
        ['Symbol', payload.symbol],
        ['Last price', payload.last_price],
        ['Last market event', payload.last_market_event_at],
        ['Current signal', payload.current_signal],
      ]);
      setPairs('account', [
        ['Paper equity', payload.paper_equity],
        ['Realized PnL', payload.realized_pnl],
        ['Unrealized PnL', payload.unrealized_pnl],
        ['Simulated', payload.simulated],
      ]);
      const position = payload.current_position || {{}};
      setPairs('position', [
        ['Symbol', position.symbol],
        ['Side', position.side],
        ['Quantity', position.quantity],
        ['Average entry', position.average_entry_price],
        ['Mark price', position.mark_price],
        ['Unrealized PnL', position.unrealized_pnl],
        ['Updated', position.updated_at],
      ]);
      document.getElementById('last-trades').innerHTML =
        renderRows(payload.recent_fills || [], [
          {{key: 'filled_at', label: 'Filled'}},
          {{key: 'side', label: 'Side'}},
          {{key: 'quantity', label: 'Qty'}},
          {{key: 'price', label: 'Price'}},
          {{key: 'order_id', label: 'Order'}},
        ]);
      document.getElementById('orders').innerHTML = renderRows(payload.recent_orders || [], [
          {{key: 'created_at', label: 'Created'}},
          {{key: 'side', label: 'Side'}},
          {{key: 'quantity', label: 'Qty'}},
          {{key: 'status', label: 'Status'}},
          {{key: 'order_id', label: 'Order'}},
        ]);
      document.getElementById('events').innerHTML = renderRows(payload.recent_events || [], [
        {{key: 'occurred_at', label: 'Occurred'}},
        {{key: 'event_type', label: 'Event'}},
        {{key: 'symbol', label: 'Symbol'}},
      ]);
    }}

    async function refresh() {{
      if (!statusUrl) {{
        render(config.fixturePayload);
        return;
      }}
      try {{
        const response = await fetch(statusUrl, {{cache: 'no-store'}});
        if (!response.ok) throw new Error(`status endpoint returned ${{response.status}}`);
        render(await response.json());
      }} catch (error) {{
        setStatus(null, `Status endpoint unavailable: ${{error.message}}`);
      }}
    }}

    refresh();
    window.setInterval(refresh, pollMs);
  </script>
</body>
</html>
"""


def _write_index_html_legacy(*, output_dir: Path, artifacts: list[DemoArtifact]) -> Path:
    cards: list[str] = []
    for item in artifacts:
        status_class = item.status
        if item.status == "ok" and (output_dir / item.filename).exists():
            link = f'<p><a class="btn" href="{item.filename}">Open dashboard</a></p>'
        else:
            link = f'<p class="meta">Not generated ({item.status}).</p>'
        cards.append(
            f"""
            <article class="card {status_class}">
              <h2>{item.title}</h2>
              <p class="workflow">{item.workflow}</p>
              <p>{item.description}</p>
              {link}
            </article>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trading Research Framework — Portfolio Demo</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f1419;
      --panel: #1a2332;
      --text: #e7ecf3;
      --muted: #9aa7b8;
      --accent: #3d8bfd;
      --ok: #3dd68c;
      --skip: #f0b429;
      --fail: #ff6b6b;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header, main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 2rem 1.25rem;
    }}
    header {{
      border-bottom: 1px solid #2a3545;
    }}
    h1 {{ margin: 0 0 0.5rem; font-size: 1.8rem; }}
    .lead {{ color: var(--muted); max-width: 70ch; }}
    .flows {{
      display: grid;
      gap: 1rem;
      margin: 2rem 0;
    }}
    .flow {{
      background: var(--panel);
      border: 1px solid #2a3545;
      border-radius: 10px;
      padding: 1rem 1.25rem;
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.92rem;
      white-space: pre-wrap;
    }}
    .grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .card {{
      background: var(--panel);
      border: 1px solid #2a3545;
      border-radius: 10px;
      padding: 1.25rem;
    }}
    .card.ok {{ border-left: 4px solid var(--ok); }}
    .card.skipped {{ border-left: 4px solid var(--skip); }}
    .card.failed {{ border-left: 4px solid var(--fail); }}
    .workflow {{
      color: var(--muted);
      font-size: 0.9rem;
      font-family: Consolas, monospace;
    }}
    .btn {{
      display: inline-block;
      margin-top: 0.75rem;
      padding: 0.55rem 0.9rem;
      border-radius: 8px;
      background: var(--accent);
      color: white;
      text-decoration: none;
      font-weight: 600;
    }}
    .meta {{ color: var(--muted); font-size: 0.9rem; }}
    footer {{
      color: var(--muted);
      font-size: 0.85rem;
      padding: 0 1.25rem 2rem;
      max-width: 1100px;
      margin: 0 auto;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Trading Research Framework</h1>
    <p class="lead">
      Offline portfolio demo: reproducible research workflows from published market data
      through analysis, declarative models, signal research, and bar-sequential strategy simulation.
      Every artifact is a standalone HTML file (no server required).
    </p>
  </header>
  <main>
    <section class="flows">
      <div class="flow">Data: CSV / Databento DBN → normalize → Parquet → publish → query
Continuous: contracts → roll schedule → NQ.c.0 trades + OHLCV</div>
      <div class="flow">Analysis: component DAG → MTF resample/align → AnalysisFrame
Models: Market Model x Signal Model (declarative expressions)</div>
      <div class="flow">Signal Research: occurrences → forward outcomes → analytics report
Strategy Research: gated entries → Numba simulator → trades + equity → dashboard</div>
    </section>
    <section class="grid">
      {"".join(cards)}
    </section>
  </main>
  <footer>
    Regenerate: <code>uv run python scripts/demo/run_portfolio_demo.py --full</code>
    · Plotly reports: <code>uv pip install plotly</code>
  </footer>
</body>
</html>
"""
    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path


def _portfolio_artifacts(output_dir: Path, artifacts: list[DemoArtifact]) -> list[DemoArtifact]:
    """Return generated artifacts plus known portfolio reports already present on disk."""

    seen = {item.filename for item in artifacts}
    display_artifacts = list(artifacts)
    for item in _KNOWN_PORTFOLIO_ARTIFACTS:
        if item.filename in seen or not (output_dir / item.filename).exists():
            continue
        display_artifacts.append(item)
        seen.add(item.filename)
    return display_artifacts


def _artifact_link(output_dir: Path, item: DemoArtifact, label: str) -> str:
    if item.status == "ok" and (output_dir / item.filename).exists():
        escaped_filename = html.escape(item.filename)
        escaped_label = html.escape(label)
        return f'<a class="btn" href="{escaped_filename}">{escaped_label}</a>'
    return f'<span class="meta">Not generated ({html.escape(item.status)}).</span>'


def _write_index_html(
    *,
    output_dir: Path,
    artifacts: list[DemoArtifact],
    live_demo_url: str = _PUBLIC_LIVE_DEMO_URL,
) -> Path:
    display_artifacts = _portfolio_artifacts(output_dir, artifacts)
    live_artifact = next(
        (item for item in display_artifacts if item.filename == _LIVE_DRY_RUN_DASHBOARD_NAME),
        None,
    )
    live_url = live_demo_url.strip()
    if not live_url and live_artifact is not None:
        live_url = live_artifact.filename

    live_static_link = ""
    if live_artifact is not None and (output_dir / live_artifact.filename).exists():
        live_static_link = _artifact_link(output_dir, live_artifact, "Open static fallback")

    cards: list[str] = []
    for item in display_artifacts:
        if item.filename == _LIVE_DRY_RUN_DASHBOARD_NAME:
            continue
        link = _artifact_link(output_dir, item, "Open report")
        cards.append(
            f"""
            <article class="card {html.escape(item.status)}">
              <p class="eyebrow">{html.escape(item.workflow)}</p>
              <h3>{html.escape(item.title)}</h3>
              <p>{html.escape(item.description)}</p>
              <p>{link}</p>
            </article>
            """
        )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trading Research Framework Portfolio Demo</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0d1014;
      --surface: #151a20;
      --panel: #1c232b;
      --line: #303a46;
      --text: #eef2f6;
      --muted: #a8b2bf;
      --accent: #4aa3ff;
      --accent-strong: #63d297;
      --warn: #f4bf5f;
      --fail: #ff736f;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
    }}
    header, main, footer {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 0 1.25rem;
    }}
    header {{
      padding-top: 2rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid var(--line);
    }}
    main {{ padding-top: 1.5rem; padding-bottom: 2rem; }}
    h1 {{ margin: 0 0 0.5rem; font-size: clamp(2rem, 5vw, 4rem); line-height: 1.02; }}
    h2 {{ margin: 0 0 1rem; font-size: 1.35rem; }}
    h3 {{ margin: 0.25rem 0 0.5rem; font-size: 1.08rem; }}
    p {{ margin: 0.5rem 0; }}
    .lead {{ color: var(--muted); max-width: 78ch; font-size: 1.02rem; }}
    .hero-grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
      margin: 1.25rem 0 1.75rem;
    }}
    .live-panel, .method-panel, .flow-card, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .live-panel {{
      padding: 1.25rem;
      border-color: #3e5e7f;
    }}
    .live-title {{
      display: flex;
      gap: 0.75rem;
      align-items: center;
      flex-wrap: wrap;
    }}
    .live-title h2 {{ margin: 0; font-size: clamp(1.5rem, 3vw, 2.25rem); }}
    .status-pill, .tag {{
      display: inline-flex;
      align-items: center;
      min-height: 1.7rem;
      padding: 0.15rem 0.55rem;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      font-size: 0.8rem;
      white-space: nowrap;
    }}
    .status-pill {{ color: #d9ffe9; border-color: #3a7f57; background: #13261c; }}
    .tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-top: 1rem;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.6rem;
      margin-top: 1rem;
      align-items: center;
    }}
    .method-panel {{
      padding: 1rem;
      background: var(--surface);
    }}
    .method-panel ol {{
      margin: 0.75rem 0 0;
      padding-left: 1.2rem;
      color: var(--muted);
    }}
    .method-panel li {{ margin: 0.45rem 0; }}
    .flows {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.9rem;
      margin: 1.5rem 0;
    }}
    .flow-card {{
      padding: 1rem;
      background: var(--surface);
    }}
    .flow-title {{
      color: var(--text);
      font-weight: 700;
      margin-bottom: 0.5rem;
    }}
    .flow {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 0.86rem;
      white-space: pre-wrap;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .card {{
      padding: 1.25rem;
    }}
    .card.ok {{ border-left: 4px solid var(--accent-strong); }}
    .card.skipped {{ border-left: 4px solid var(--warn); }}
    .card.failed {{ border-left: 4px solid var(--fail); }}
    .eyebrow {{
      color: var(--muted);
      font-size: 0.78rem;
      font-family: Consolas, monospace;
      min-height: 2.4rem;
    }}
    .btn {{
      display: inline-block;
      margin-top: 0.75rem;
      padding: 0.55rem 0.9rem;
      border-radius: 8px;
      background: var(--accent);
      color: white;
      text-decoration: none;
      font-weight: 600;
    }}
    .meta {{ color: var(--muted); font-size: 0.9rem; }}
    .section-title {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: end;
      margin: 2rem 0 1rem;
      border-top: 1px solid var(--line);
      padding-top: 1rem;
    }}
    footer {{
      color: var(--muted);
      font-size: 0.85rem;
      padding-bottom: 2rem;
    }}
    @media (max-width: 800px) {{
      .hero-grid, .flows {{ grid-template-columns: 1fr; }}
      .section-title {{ display: block; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Trading Research Framework Portfolio</h1>
    <p class="lead">
      A portfolio hub for the framework behind the charts: market data normalization,
      reusable analysis components, declarative models, signal research, strategy simulation,
      robustness checks and a live AWS dry-run runtime.
    </p>
  </header>
  <main>
    <section class="hero-grid" aria-label="Featured live dry run">
      <article class="live-panel">
        <div class="live-title">
          <span class="status-pill">Live dry-run</span>
          <h2>BTCUSDT execution demo on AWS</h2>
        </div>
        <p class="lead">
          The primary portfolio view is the running dry-run: real Binance USD-M BTCUSDT market data,
          simulated orders only, persisted runtime state and a live VPS dashboard with candles,
          fills, current position, equity and heartbeat freshness.
        </p>
        <div class="tags">
          <span class="tag">ECS Fargate worker</span>
          <span class="tag">DynamoDB state</span>
          <span class="tag">Lambda status API</span>
          <span class="tag">SQLite dashboard history</span>
          <span class="tag">No real capital</span>
        </div>
        <div class="actions">
          <a class="btn" href="{html.escape(live_url)}">Open live dashboard</a>
          {live_static_link}
        </div>
      </article>
      <aside class="method-panel">
        <h2>What this proves</h2>
        <ol>
          <li>Research artifacts are reproducible, not screenshots.</li>
          <li>Strategy logic can run against live market data without exchange risk.</li>
          <li>Execution state survives worker restarts and feeds a public read model.</li>
          <li>The same framework separates data, models, simulation and execution.</li>
        </ol>
      </aside>
    </section>

    <section class="flows">
      <div class="flow-card">
        <div class="flow-title">1. Data foundation</div>
        <div class="flow">CSV / DBN -> normalize -> Parquet -> publish -> query
Contracts -> roll schedule -> continuous futures -> OHLCV/trades</div>
      </div>
      <div class="flow-card">
        <div class="flow-title">2. Research engine</div>
        <div class="flow">Market facts -> component DAG -> AnalysisFrame
Market Model x Signal Model -> occurrences -> forward outcomes</div>
      </div>
      <div class="flow-card">
        <div class="flow-title">3. Strategy and execution</div>
        <div class="flow">Signal gates -> risk model -> bar-sequential simulator -> trades/equity
Live adapter -> simulated orders -> persisted dry-run status</div>
      </div>
    </section>

    <section class="section-title">
      <div>
        <h2>Reports And Workflow Evidence</h2>
        <p class="meta">
          Each tile is a browser-openable artifact. Charts show results; workflow labels show how
          the framework produced them.
        </p>
      </div>
    </section>
    <section class="grid">
      {"".join(cards)}
    </section>
  </main>
  <footer>
    Regenerate: <code>uv run python scripts/demo/run_portfolio_demo.py --full</code>
    | Plotly reports: <code>uv pip install plotly</code>
  </footer>
</body>
</html>
"""
    index_path = output_dir / "index.html"
    index_path.write_text(page, encoding="utf-8")
    return index_path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[DemoArtifact] = []
    artifacts.append(
        _build_live_dry_run_dashboard(
            output_dir=output_dir,
            status_url=args.live_status_url,
        )
    )

    if args.full:
        half_year_path = output_dir / _HALF_YEAR_DASHBOARD_NAME
        artifacts.append(
            _build_half_year_strategy_dashboard(
                storage_root=args.half_year_storage.resolve(),
                output_path=half_year_path,
                refresh=args.refresh_half_year,
            )
        )

    with tempfile.TemporaryDirectory(prefix="portfolio_demo_") as tmp:
        workspace = Path(tmp)
        artifacts.append(
            _build_fixture_strategy_dashboard(
                workspace=workspace,
                output_path=output_dir / _FIXTURE_DASHBOARD_NAME,
            )
        )

    use_plotly = not args.skip_plotly
    if use_plotly and not _plotly_available():
        print(
            "[demo] plotly not installed — skipping inspection reports. "
            "Install with: uv pip install plotly",
            file=sys.stderr,
        )
        use_plotly = False

    if use_plotly:
        plotly_jobs = [
            (
                "tests/spike/run_signal_research_analytics_report.py",
                "02_signal_research_analytics.html",
                [],
                DemoArtifact(
                    filename="02_signal_research_analytics.html",
                    title="Signal Research Analytics Report",
                    workflow="Signal Research run → analyze → grouped metrics HTML",
                    description=(
                        "RTH grouping, conditional context, horizon summaries on fixture data."
                    ),
                    status="ok",
                ),
                True,
            ),
            (
                "tests/spike/run_inspect_combined_research.py",
                "03_combined_research_inspection.html",
                ["--scope", "market_and_signal"],
                DemoArtifact(
                    filename="03_combined_research_inspection.html",
                    title="Combined Research Inspection",
                    workflow="MARKET_AND_SIGNAL → outcome window chart",
                    description=(
                        "OHLCV window with MFE/MAE, terminal outcome and context at available_at."
                    ),
                    status="ok",
                ),
                True,
            ),
            (
                "tests/spike/run_inspect_declarative_models.py",
                "04_model_inspection.html",
                [
                    "--market-models",
                    "high_volatility",
                    "--signal-models",
                    "higher_low_long,high_vol_and_higher_low",
                ],
                DemoArtifact(
                    filename="04_model_inspection.html",
                    title="Declarative Model Inspection",
                    workflow="evaluate_models → overlay state/conditions/emissions",
                    description="Market + signal model overlays on the same AnalysisFrame.",
                    status="ok",
                ),
                False,
            ),
            (
                "tests/spike/run_inspect_signal_research.py",
                "05_signal_occurrence_inspection.html",
                [],
                DemoArtifact(
                    filename="05_signal_occurrence_inspection.html",
                    title="Signal Occurrence Inspection",
                    workflow="Signal Research → single occurrence drill-down",
                    description="Marker, reference price, horizon end and excursion levels.",
                    status="ok",
                ),
                True,
            ),
            (
                "tests/spike/run_inspect_mtf_swing.py",
                "06_mtf_swing_inspection.html",
                ["--pivot-range", "2"],
                DemoArtifact(
                    filename="06_mtf_swing_inspection.html",
                    title="MTF Swing Structure Inspection",
                    workflow="run_analysis → swing structure + RTH shading",
                    description="Multitimeframe swing events, state levels and session boundaries.",
                    status="ok",
                ),
                False,
            ),
        ]
        for script, filename, extra_args, template, generate in plotly_jobs:
            artifacts.append(
                _build_plotly_report(
                    script_relpath=script,
                    output_path=output_dir / filename,
                    extra_args=extra_args,
                    artifact=template,
                    generate=generate,
                )
            )

    index_path = _write_index_html(
        output_dir=output_dir,
        artifacts=artifacts,
        live_demo_url=args.live_demo_url,
    )
    print(f"[demo] portfolio index: {index_path}")

    ok_count = sum(1 for item in artifacts if item.status == "ok")
    print(f"[demo] artifacts ok: {ok_count}/{len(artifacts)}")
    print(f"[demo] index links shown: {len(_portfolio_artifacts(output_dir, artifacts))}")

    if args.open:
        webbrowser.open(index_path.as_uri())

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
