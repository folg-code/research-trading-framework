"""Compare persisted Predictive Research runs on one dataset fingerprint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.predictive_research import (
    ComparePredictiveRunsRequest,
    compare_predictive_runs,
)
from trading_framework.core.exceptions import ValidationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rank Predictive Research runs that share one dataset fingerprint "
            "and write leaderboard.json."
        ),
    )
    parser.add_argument(
        "--run-dir",
        action="append",
        required=True,
        type=Path,
        dest="run_dirs",
        help="Path to one persisted run directory (repeat for each run)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination JSON path (default: leaderboard.json next to the first run)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the leaderboard as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = compare_predictive_runs(
            ComparePredictiveRunsRequest(
                run_dirs=tuple(args.run_dirs),
                output_path=args.output,
            )
        )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = result.leaderboard.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"dataset_fingerprint: {payload['dataset_fingerprint']}")
        print(f"metric: {payload['metric']}")
        print(f"output: {result.output_path}")
        for row in payload["rows"]:
            score = row["pooled_primary"]
            print(
                f"{row['rank']:>3}  {row['kind']:<10}  {row['family']:<24}  "
                f"{score if score is not None else 'null'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
