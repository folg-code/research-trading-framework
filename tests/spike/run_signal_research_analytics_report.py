"""S010-T009 — Signal Research analytics HTML report spike.

Run manually:

    uv pip install plotly
    uv run python tests/spike/run_signal_research_analytics_report.py --generate --open
    uv run python tests/spike/run_signal_research_analytics_report.py \\
        --storage-root user_data/storage --run-id <run_id> --open

The report consumes ``AnalyzeSignalResearchResult`` only — no Parquet reads or recomputation.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import webbrowser
from pathlib import Path

_SPIKE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SPIKE_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.spike._fixture_paths import OHLCV_SAMPLE_1M
from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.signal_research import (
    AnalyzeSignalResearchRequest,
    RunSignalResearchRequest,
    analyze_signal_research_run,
    run_signal_research,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.analytics import GroupDimension
from trading_framework.research.analytics.reports import render_signal_research_report
from trading_framework.research.datasets import RunDatasetRef
from trading_framework.research.scope import ResearchScope
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

_FIXTURE = OHLCV_SAMPLE_1M
_FIXTURE_VOLATILITY_THRESHOLD = 0.5
_HORIZON = 5
_DEFAULT_OUTPUT = Path("signal_research_analytics_report.html")


def _write_published_dataset(storage_root: Path, csv_path: Path) -> DatasetRef:
    from datetime import UTC

    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="s010-analytics-report",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
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


def _resolve_run_ref(
    *,
    storage_root: Path,
    run_id: str | None,
    generate: bool,
) -> RunDatasetRef:
    if run_id is not None:
        return RunDatasetRef(run_id=run_id)
    if not generate:
        msg = "provide --run-id or pass --generate to materialize a fixture run"
        raise SystemExit(msg)

    dataset_ref = _write_published_dataset(storage_root, _FIXTURE)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    market_model = build_canonical_market_model_high_volatility(
        threshold=_FIXTURE_VOLATILITY_THRESHOLD
    )
    signal_model = build_canonical_signal_higher_low_on_event()
    run_result = run_signal_research(
        RunSignalResearchRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            scope=ResearchScope.MARKET_AND_SIGNAL,
            market_models=(market_model,),
            signal_models=(signal_model,),
            horizons=(_HORIZON,),
            evaluation_timeframe=Timeframe("1m"),
            session_resolver=CmeEsRthSessionResolver(),
        )
    )
    return run_result.run_ref


def main() -> int:
    parser = argparse.ArgumentParser(description="Signal Research analytics HTML report spike")
    parser.add_argument("--storage-root", type=Path, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    if args.storage_root is None:
        with tempfile.TemporaryDirectory() as tmp:
            storage_root = Path(tmp) / "storage"
            storage_root.mkdir()
            return _run(
                storage_root=storage_root,
                run_id=args.run_id,
                generate=args.generate or args.run_id is None,
                output=args.output,
                open_browser=args.open,
            )

    return _run(
        storage_root=args.storage_root,
        run_id=args.run_id,
        generate=args.generate,
        output=args.output,
        open_browser=args.open,
    )


def _run(
    *,
    storage_root: Path,
    run_id: str | None,
    generate: bool,
    output: Path,
    open_browser: bool,
) -> int:
    run_ref = _resolve_run_ref(storage_root=storage_root, run_id=run_id, generate=generate)
    result = analyze_signal_research_run(
        AnalyzeSignalResearchRequest(
            run_ref=run_ref,
            storage_root=storage_root,
            horizons=(_HORIZON,),
            group_by=(GroupDimension.RTH_MEMBERSHIP,),
            conditional_context=True,
        )
    )
    report_path = render_signal_research_report(result, output)
    print(f"Wrote report: {report_path.resolve()}")
    if open_browser:
        webbrowser.open(report_path.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
