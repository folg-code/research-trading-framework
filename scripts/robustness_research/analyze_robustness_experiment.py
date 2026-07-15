"""Analyze a robustness experiment and evaluate verdict gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.robustness_research import (
    AnalyzeRobustnessExperimentRequest,
    analyze_robustness_experiment,
)
from trading_framework.core.exceptions import ValidationError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a robustness experiment and evaluate verdict gates.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--json", action="store_true", help="Print verdict as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = analyze_robustness_experiment(
            AnalyzeRobustnessExperimentRequest(
                experiment_id=args.experiment_id,
                storage_root=args.storage_root,
            )
        )
    except (ValidationError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.verdict.to_dict(), indent=2))
    else:
        print(f"verdict: {result.verdict.verdict.value}")
        print(result.verdict.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
