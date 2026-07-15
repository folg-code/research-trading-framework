"""Render one Signal Research HTML dashboard report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.signal_research import (
    RenderSignalResearchReportRequest,
    render_signal_research_report,
)
from trading_framework.core.exceptions import ValidationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render one Signal Research HTML dashboard report.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--definition",
        type=Path,
        help="Optional definition file when cached analytics is unavailable",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output HTML path (defaults to run report/report.html)",
    )
    parser.add_argument(
        "--recompute-analytics",
        action="store_true",
        help="Ignore cached analytics/summary.json and recompute aggregates",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print render result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = render_signal_research_report(
            RenderSignalResearchReportRequest(
                storage_root=args.storage_root,
                run_id=args.run_id,
                output_path=args.output,
                definition_path=args.definition,
                use_cached_analytics=not args.recompute_analytics,
            )
        )
    except (ValidationError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "output_path": str(result.output_path),
        "source_run_id": result.source_run_id,
        "used_cached_analytics": result.used_cached_analytics,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Wrote Signal Research report: {result.output_path}")
        print(f"used_cached_analytics: {result.used_cached_analytics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
