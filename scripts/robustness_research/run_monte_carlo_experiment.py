"""Run Monte Carlo paths for a declared robustness experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.robustness_research import (
    RunMonteCarloExperimentRequest,
    run_monte_carlo_experiment,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.datasets.robustness import RobustnessExperimentRepository
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Monte Carlo simulation for a robustness experiment.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo = RobustnessExperimentRepository(args.storage_root)
    try:
        manifest = repo.read_manifest(args.experiment_id)
        dataset_ref = DatasetRef.parse(manifest.spec.dataset_ref)
        metadata = FileDatasetRegistry(args.storage_root).get(dataset_ref)
        result = run_monte_carlo_experiment(
            RunMonteCarloExperimentRequest(
                spec=manifest.spec,
                storage_root=args.storage_root,
                dataset_ref=dataset_ref,
                timeframe=Timeframe(manifest.spec.timeframe),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=Timeframe(
                    manifest.spec.evaluation_timeframe or manifest.spec.timeframe
                ),
                session_resolver=CmeEsRthSessionResolver(),
            )
        )
    except (ValidationError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.results.to_dict(), indent=2))
    else:
        print(f"experiment_id: {result.experiment_id}")
        print(f"reference_run_id: {result.results.reference_strategy_run_id}")
        print(f"skipped: {result.skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
