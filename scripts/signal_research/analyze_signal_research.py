"""Analyze one persisted Signal Research run and optionally cache analytics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.signal_research import (
    analyze_signal_research_run,
    map_definition_to_analyze_request,
    persist_signal_research_analytics,
    resolve_signal_research_definition,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.signal_research import RunDatasetRef
from trading_framework.research.signal_research.loader import load_signal_research_definition


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one persisted Signal Research run.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--definition",
        type=Path,
        help="Optional definition file for grouping and quality rules",
    )
    parser.add_argument(
        "--persist-analytics",
        action="store_true",
        help="Write analytics/summary.json sidecar for fast re-reporting",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print analytics summary as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run_ref = RunDatasetRef(run_id=args.run_id)
    try:
        if args.definition is not None:
            spec = load_signal_research_definition(args.definition)
            resolved = resolve_signal_research_definition(spec)
            analyze_request = map_definition_to_analyze_request(
                resolved,
                run_ref=run_ref,
                storage_root=args.storage_root,
            )
        else:
            from trading_framework.application.signal_research.analyze_signal_research import (
                AnalyzeSignalResearchRequest,
            )
            from trading_framework.research.datasets.signal_research import (
                SignalResearchDatasetRepository,
            )
            from trading_framework.research.scope import ResearchScope

            repo = SignalResearchDatasetRepository(args.storage_root)
            envelope = repo.read(run_ref)
            scope = envelope.manifest.effective_scope()
            analyze_request = AnalyzeSignalResearchRequest(
                run_ref=run_ref,
                storage_root=args.storage_root,
                conditional_context=scope is ResearchScope.MARKET_AND_SIGNAL,
            )

        result = analyze_signal_research_run(analyze_request)
        summary_path = None
        if args.persist_analytics:
            persisted = persist_signal_research_analytics(
                result,
                storage_root=args.storage_root,
            )
            summary_path = persisted.summary_path
    except (ValidationError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    primary = result.run_summaries.sort("horizon_bars").row(0, named=True)
    payload = {
        "source_run_id": result.source_run_id,
        "primary_horizon_bars": int(primary["horizon_bars"]),
        "sample_size_complete": int(primary["sample_size_complete"]),
        "quality_warning_count": len(result.quality_warnings),
        "analytics_summary_path": str(summary_path) if summary_path is not None else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"source_run_id: {payload['source_run_id']}")
        print(f"primary_horizon_bars: {payload['primary_horizon_bars']}")
        print(f"sample_size_complete: {payload['sample_size_complete']}")
        print(f"quality_warning_count: {payload['quality_warning_count']}")
        if summary_path is not None:
            print(f"analytics_summary_path: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
