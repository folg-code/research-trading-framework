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
import importlib.util
import subprocess
import sys
import tempfile
import webbrowser
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OHLCV_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "market_data" / "ohlcv_sample_1m.csv"

_DEFAULT_OUTPUT = _REPO_ROOT / "demo" / "output"
_DEFAULT_HALF_YEAR_STORAGE = _REPO_ROOT / "user_data" / "storage_nq_half_year"
_HALF_YEAR_DASHBOARD_NAME = "00_strategy_dashboard_nq_half_year.html"
_FIXTURE_DASHBOARD_NAME = "01_strategy_dashboard_fixture.html"


@dataclass(frozen=True, slots=True)
class DemoArtifact:
    """One generated HTML artifact shown on the portfolio index."""

    filename: str
    title: str
    workflow: str
    description: str
    status: str  # ok | skipped | failed


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


def _write_published_fixture_dataset(storage_root: Path):
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

    runs_dir = storage_root / "strategy_research"
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


def _write_index_html(*, output_dir: Path, artifacts: list[DemoArtifact]) -> Path:
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


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[DemoArtifact] = []

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

    index_path = _write_index_html(output_dir=output_dir, artifacts=artifacts)
    print(f"[demo] portfolio index: {index_path}")

    ok_count = sum(1 for item in artifacts if item.status == "ok")
    print(f"[demo] artifacts ok: {ok_count}/{len(artifacts)}")

    if args.open:
        webbrowser.open(index_path.as_uri())

    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
