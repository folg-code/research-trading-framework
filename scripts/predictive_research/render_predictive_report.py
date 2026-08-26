"""Render an offline HTML report for one persisted Predictive Research run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.predictive_research import (
    RenderPredictiveReportRequest,
    render_predictive_research_report,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.predictive_run import PredictiveRunRef


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a standalone Predictive Research HTML report from a persisted run.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Workspace root (contains market_data/ and research/)",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Persisted Predictive Research run_id",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="HTML output path (default: <run-dir>/report.html)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print render summary as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = render_predictive_research_report(
            RenderPredictiveReportRequest(
                run_ref=PredictiveRunRef(run_id=args.run_id),
                storage_root=args.storage_root,
                output_path=args.output,
            )
        )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {"run_id": result.run_id, "output_path": str(result.output_path)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"run_id: {payload['run_id']}")
        print(f"output_path: {payload['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
