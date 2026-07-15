"""Render a robustness experiment HTML dashboard report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trading_framework.application.robustness_research import (
    RenderRobustnessReportRequest,
    render_robustness_experiment_report,
)
from trading_framework.core.exceptions import ValidationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a robustness experiment HTML dashboard report.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output HTML path (defaults to experiment report dir)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = render_robustness_experiment_report(
            RenderRobustnessReportRequest(
                experiment_id=args.experiment_id,
                storage_root=args.storage_root,
                output_path=args.output,
            )
        )
    except (ValidationError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote robustness report: {result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
