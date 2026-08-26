"""Analyze one persisted Predictive Research run and write metrics.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.predictive_research import (
    AnalyzePredictiveRunRequest,
    analyze_predictive_run,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.predictive_run import PredictiveRunRef


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze one persisted Predictive Research run (predictions + metrics).",
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
        "--json",
        action="store_true",
        help="Print analysis summary as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = analyze_predictive_run(
            AnalyzePredictiveRunRequest(
                run_ref=PredictiveRunRef(run_id=args.run_id),
                storage_root=args.storage_root,
                persist=True,
            )
        )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report_payload = result.report.to_dict()
    metrics_path = None if result.metrics_path is None else str(result.metrics_path)
    payload = {
        "run_id": result.run_id,
        "fold_count": len(report_payload["folds"]),
        "fold_ids": list(report_payload["folds"]),
        "pooled_sources": list(report_payload["pooled"]),
        "pooled": report_payload["pooled"],
        "metrics_path": metrics_path,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"run_id: {payload['run_id']}")
        print(f"fold_count: {payload['fold_count']}")
        print(f"fold_ids: {', '.join(str(item) for item in payload['fold_ids'])}")
        print(f"pooled_sources: {', '.join(str(item) for item in payload['pooled_sources'])}")
        print(f"metrics_path: {payload['metrics_path']}")
        print("per-fold metrics written under folds in metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
