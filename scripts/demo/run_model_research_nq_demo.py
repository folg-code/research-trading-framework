"""Generate Model Research Methodology HTML dashboards for three research scopes.

Default path uses the published NQ half-year continuous OHLCV storage and canonical
models from Sprint 006 (``high_volatility``, ``higher_low_long``).

    uv run python scripts/demo/run_model_research_nq_demo.py --open
    uv run python scripts/demo/run_model_research_nq_demo.py --fixture --open
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import webbrowser
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading_framework.market.datasets import DatasetRef
    from trading_framework.market_analysis.models.time_range import TimeRange
    from trading_framework.research.scope import ResearchScope
    from trading_framework.research.signal_research.definition import SignalResearchDefinitionSpec
    from trading_framework.time.sessions.protocol import TradingSessionResolver

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIXTURE_CSV = _REPO_ROOT / "tests" / "fixtures" / "market_data" / "ohlcv_sample_1m.csv"
_DEFAULT_HALF_YEAR_STORAGE = _REPO_ROOT / "user_data" / "storage_nq_half_year"
_DEFAULT_OUTPUT_INDEX = _REPO_ROOT / "demo" / "output" / "08_model_research_nq_half_year.html"
_DEFAULT_SCOPE_OUTPUT_DIR = _REPO_ROOT / "demo" / "output" / "model_research"
_FIXTURE_STORAGE = _REPO_ROOT / "demo" / "model_research_storage"
_NQ_HORIZONS = ("5m", "15m", "30m", "60m")
_FIXTURE_HORIZONS = ("5m",)


@dataclass(frozen=True, slots=True)
class _ScopeDemoConfig:
    research_id: str
    scope: ResearchScope
    market_model_id: str | None
    signal_model_id: str | None
    baseline_type: str | None
    output_filename: str
    title: str
    research_question: str
    fixture_supported: bool


def _scope_configs() -> tuple[_ScopeDemoConfig, ...]:
    from trading_framework.research.scope import ResearchScope

    return (
        _ScopeDemoConfig(
            research_id="nq_demo_market_model_only",
            scope=ResearchScope.MARKET_MODEL_ONLY,
            market_model_id="high_volatility",
            signal_model_id=None,
            baseline_type="MODEL_ACTIVE",
            output_filename="market_model_only.html",
            title="Market model only — high volatility",
            research_question=(
                "Do high-volatility market states show repeatable forward returns on NQ?"
            ),
            fixture_supported=False,
        ),
        _ScopeDemoConfig(
            research_id="nq_demo_signal_model_only",
            scope=ResearchScope.SIGNAL_MODEL_ONLY,
            market_model_id=None,
            signal_model_id="higher_low_long",
            baseline_type="AFTER_SIGNAL",
            output_filename="signal_model_only.html",
            title="Signal model only — higher low long",
            research_question=(
                "Does the higher-low long signal show repeatable forward returns on NQ?"
            ),
            fixture_supported=True,
        ),
        _ScopeDemoConfig(
            research_id="nq_demo_market_and_signal",
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_model_id="high_volatility",
            signal_model_id="higher_low_long",
            baseline_type="SIGNAL_ONLY",
            output_filename="market_and_signal.html",
            title="Combined — volatility filter x higher low",
            research_question=(
                "Does higher-low structure show repeatable forward returns when filtered "
                "by high volatility?"
            ),
            fixture_supported=True,
        ),
    )


_SCOPE_CONFIGS: tuple[_ScopeDemoConfig, ...] = _scope_configs()


def _active_scope_configs(*, fixture: bool) -> tuple[_ScopeDemoConfig, ...]:
    if not fixture:
        return _SCOPE_CONFIGS
    return tuple(config for config in _SCOPE_CONFIGS if config.fixture_supported)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Model Research Methodology HTML dashboards (3 scopes)."
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=None,
        help="Workspace for datasets and Signal Research runs (default: NQ half-year)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT_INDEX,
        help="Landing-page HTML path",
    )
    parser.add_argument(
        "--scope-output-dir",
        type=Path,
        default=_DEFAULT_SCOPE_OUTPUT_DIR,
        help="Directory for per-scope report HTML files",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use committed OHLCV fixture instead of NQ half-year storage",
    )
    parser.add_argument(
        "--refresh-runs",
        action="store_true",
        help="Delete existing demo runs before re-executing model evaluation",
    )
    parser.add_argument("--open", action="store_true", help="Open index page in default browser")
    return parser


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
        source_id="model-research-demo-fixture",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=_FIXTURE_CSV,
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


def _resolve_half_year_dataset(storage_root: Path) -> DatasetRef:
    from trading_framework.core.exceptions import ValidationError
    from trading_framework.infrastructure.storage.metadata.discovery import (
        latest_published_dataset_ref,
    )
    from trading_framework.market.continuous.identity import continuous_instrument_id
    from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
    from trading_framework.market.datasets import DatasetId
    from trading_framework.market.derivation import DERIVED_OHLCV_PROVIDER
    from trading_framework.time.models.timeframe import Timeframe

    if not storage_root.exists():
        msg = f"half-year storage not found: {storage_root}"
        raise ValidationError(msg)

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
        msg = "no published continuous NQ OHLCV dataset in half-year storage"
        raise ValidationError(msg)
    return dataset_ref


def _find_run_id_by_research_id(storage_root: Path, research_id: str) -> str | None:
    for child in sorted(storage_root.iterdir()):
        manifest_path = child / "manifest.json"
        if not manifest_path.is_file():
            continue
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("research_id") == research_id:
            return child.name
    return None


def _delete_demo_runs(storage_root: Path, research_ids: tuple[str, ...]) -> None:
    for research_id in research_ids:
        run_id = _find_run_id_by_research_id(storage_root, research_id)
        if run_id is None:
            continue
        run_dir = storage_root / run_id
        if run_dir.is_dir():
            shutil.rmtree(run_dir)


def _build_definition_spec(
    *,
    config: _ScopeDemoConfig,
    dataset_ref: DatasetRef,
    time_range: TimeRange,
    horizons: tuple[str, ...],
    fixture: bool,
) -> SignalResearchDefinitionSpec:
    from trading_framework.research.signal_research.definition import (
        BaselineType,
        OccurrencePolicy,
        OccurrencePolicyType,
        ResearchGroupingDimension,
        SignalResearchDefinitionSpec,
        SignalResearchQualityRules,
    )

    baseline = BaselineType(config.baseline_type) if config.baseline_type is not None else None
    quality_rules = SignalResearchQualityRules(
        minimum_sample_size=10 if fixture else 100,
        maximum_single_period_contribution=0.40,
    )
    return SignalResearchDefinitionSpec(
        research_id=config.research_id,
        research_scope=config.scope,
        dataset_ref=dataset_ref,
        time_range=time_range,
        horizons=horizons,
        research_question=config.research_question,
        market_model_id=config.market_model_id,
        signal_model_id=config.signal_model_id,
        grouping=(
            ResearchGroupingDimension.MONTH,
            ResearchGroupingDimension.SESSION,
            ResearchGroupingDimension.TIME_OF_DAY,
        ),
        occurrence_policy=OccurrencePolicy(type=OccurrencePolicyType.KEEP_ALL),
        quality_rules=quality_rules,
        baseline=baseline,
    )


def _run_scope_pipeline(
    *,
    config: _ScopeDemoConfig,
    dataset_ref: DatasetRef,
    time_range: TimeRange,
    storage_root: Path,
    horizons: tuple[str, ...],
    fixture: bool,
    scope_output_dir: Path,
    session_resolver: TradingSessionResolver,
) -> tuple[str, Path]:
    from trading_framework.application.signal_research import (
        analyze_signal_research_run,
        map_definition_to_analyze_request,
        map_definition_to_run_request,
        persist_signal_research_analytics,
        render_signal_research_report,
        resolve_signal_research_definition,
        run_signal_research,
    )
    from trading_framework.application.signal_research.render_signal_research_report import (
        RenderSignalResearchReportRequest,
    )
    from trading_framework.research.datasets.signal_research import RunDatasetRef

    spec = _build_definition_spec(
        config=config,
        dataset_ref=dataset_ref,
        time_range=time_range,
        horizons=horizons,
        fixture=fixture,
    )
    resolved = resolve_signal_research_definition(spec)
    run_request = map_definition_to_run_request(
        resolved,
        storage_root=storage_root,
        session_resolver=session_resolver,
        persist=True,
    )

    existing_run_id = _find_run_id_by_research_id(storage_root, config.research_id)
    if existing_run_id is not None:
        run_id = existing_run_id
        print(f"[model-research-demo] reuse run {run_id} ({config.scope.value})")
    else:
        run_result = run_signal_research(run_request)
        run_id = run_result.run_id
        print(f"[model-research-demo] persisted run {run_id} ({config.scope.value})")

    analyze_request = map_definition_to_analyze_request(
        resolved,
        run_ref=RunDatasetRef(run_id=run_id),
        storage_root=storage_root,
    )
    analytics = analyze_signal_research_run(analyze_request)
    persist_signal_research_analytics(analytics, storage_root=storage_root)

    output_path = scope_output_dir / config.output_filename
    render_result = render_signal_research_report(
        RenderSignalResearchReportRequest(
            storage_root=storage_root,
            run_id=run_id,
            output_path=output_path,
            persist_to_run_dir=False,
            use_cached_analytics=True,
        )
    )
    print(f"[model-research-demo] report: {render_result.output_path}")
    return run_id, render_result.output_path


def _write_index_html(
    *,
    output_path: Path,
    scope_output_dir: Path,
    scope_reports: list[tuple[_ScopeDemoConfig, str, Path]],
    mode_label: str,
    dataset_label: str,
    bar_count: int,
    date_range: str,
) -> Path:
    cards: list[str] = []
    for config, run_id, report_path in scope_reports:
        relative_href = report_path.relative_to(output_path.parent).as_posix()
        cards.append(
            f"""
            <article class="card">
              <h2>{config.title}</h2>
              <p class="meta">Scope: {config.scope.value} · run_id: {run_id}</p>
              <p>{config.research_question}</p>
              <p><a class="btn" href="{relative_href}">Open dashboard</a></p>
            </article>
            """
        )

    scope_dir_label = (
        scope_output_dir.relative_to(_REPO_ROOT).as_posix()
        if scope_output_dir.is_relative_to(_REPO_ROOT)
        else str(scope_output_dir)
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Model Research Methodology — NQ Half-Year Demo</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f1419;
      --panel: #1a2332;
      --text: #e7ecf3;
      --muted: #9aa7b8;
      --accent: #3d8bfd;
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
    header {{ border-bottom: 1px solid #2a3545; }}
    h1 {{ margin: 0 0 0.5rem; font-size: 1.8rem; }}
    .lead {{ color: var(--muted); max-width: 72ch; }}
    .flow {{
      background: var(--panel);
      border: 1px solid #2a3545;
      border-radius: 10px;
      padding: 1rem 1.25rem;
      margin: 1.5rem 0;
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
      border-left: 4px solid var(--accent);
      border-radius: 10px;
      padding: 1.25rem;
    }}
    .meta {{ color: var(--muted); font-size: 0.9rem; }}
    .btn {{
      display: inline-block;
      margin-top: 0.5rem;
      padding: 0.45rem 0.9rem;
      background: var(--accent);
      color: #fff;
      text-decoration: none;
      border-radius: 6px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Model Research Methodology — Sprint 017</h1>
    <p class="lead">
      Three bounded Signal Research scopes over the same dataset: market model only,
      signal model only, and combined market x signal with baseline comparison.
      Mode: <strong>{mode_label}</strong>.
    </p>
  </header>
  <main>
    <div class="flow">SignalResearchDefinitionSpec
  → run_signal_research (scope-aware)
  → analyze_signal_research_run + quality flags
  → build_signal_research_report (Plotly HTML)

Dataset: {dataset_label}
Bars: {bar_count:,}
Range: {date_range}
Reports: {scope_dir_label}/</div>
    <div class="grid">
      {"".join(cards)}
    </div>
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _require_plotly() -> None:
    import importlib

    try:
        importlib.import_module("plotly")
    except ImportError:
        print(
            "[model-research-demo] plotly is required. Install with: uv pip install plotly",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def main(argv: list[str] | None = None) -> int:
    _require_plotly()

    args = _build_parser().parse_args(argv)
    from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
    from trading_framework.market_analysis import TimeRange
    from trading_framework.time.sessions import CmeEsRthSessionResolver

    use_fixture = args.fixture
    storage_root = (
        args.storage_root
        if args.storage_root is not None
        else (_FIXTURE_STORAGE if use_fixture else _DEFAULT_HALF_YEAR_STORAGE)
    )
    horizons = _FIXTURE_HORIZONS if use_fixture else _NQ_HORIZONS
    scope_configs = _active_scope_configs(fixture=use_fixture)
    research_ids = tuple(config.research_id for config in scope_configs)

    storage_root.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.scope_output_dir.mkdir(parents=True, exist_ok=True)

    if args.refresh_runs:
        _delete_demo_runs(storage_root, research_ids)

    mode_label = "fixture (ES CSV, 2 scopes)" if use_fixture else "NQ half-year (3 scopes)"
    print(f"[model-research-demo] mode: {mode_label}")
    print(f"[model-research-demo] storage: {storage_root}")

    if use_fixture:
        dataset_ref = _write_published_fixture_dataset(storage_root)
    else:
        dataset_ref = _resolve_half_year_dataset(storage_root)

    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    print(
        f"[model-research-demo] dataset: {dataset_ref} "
        f"({metadata.row_count:,} bars, {requested_range.start.date()} .. "
        f"{requested_range.end.date()})"
    )

    session_resolver = CmeEsRthSessionResolver()
    scope_reports: list[tuple[_ScopeDemoConfig, str, Path]] = []
    for config in scope_configs:
        run_id, report_path = _run_scope_pipeline(
            config=config,
            dataset_ref=dataset_ref,
            time_range=requested_range,
            storage_root=storage_root,
            horizons=horizons,
            fixture=use_fixture,
            scope_output_dir=args.scope_output_dir,
            session_resolver=session_resolver,
        )
        scope_reports.append((config, run_id, report_path))

    index_path = _write_index_html(
        output_path=args.output,
        scope_output_dir=args.scope_output_dir,
        scope_reports=scope_reports,
        mode_label=mode_label,
        dataset_label=str(dataset_ref),
        bar_count=metadata.row_count,
        date_range=(
            f"{requested_range.start.date().isoformat()} .. "
            f"{requested_range.end.date().isoformat()}"
        ),
    )
    print(f"[model-research-demo] index: {index_path}")

    if args.open:
        webbrowser.open(index_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
