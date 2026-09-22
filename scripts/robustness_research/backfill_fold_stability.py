"""Backfill Sprint 075 walk-forward fold geometry and stability for one experiment.

Phase 18, 18D Milestone 1 (D-P18D-01/02). Computes both new artifacts
post-hoc, purely from data the experiment already persists -- the fold
date ranges in ``folds/plan.json`` and the per-fold PnL already written to
``analytics/walk_forward_folds.parquet``. Does NOT rerun the fold planner,
the parameter sweep, or any backtest.

    uv run python scripts/robustness_research/backfill_fold_stability.py \\
        --storage-root user_data --experiment-id <experiment_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from trading_framework.infrastructure.storage.paths import (  # noqa: E402
    robustness_experiment_analytics_parquet_path,
)
from trading_framework.research.datasets.robustness import (  # noqa: E402
    RobustnessExperimentRepository,
)
from trading_framework.research.robustness.analytics.fold_stability import (  # noqa: E402
    compute_walk_forward_fold_geometry,
    compute_walk_forward_stability,
)


def backfill_experiment(*, storage_root: Path, experiment_id: str) -> None:
    repo = RobustnessExperimentRepository(storage_root)
    plan = repo.read_walk_forward_plan(experiment_id)
    geometry = compute_walk_forward_fold_geometry(experiment_id=experiment_id, plan=plan)
    geometry.write_parquet(
        robustness_experiment_analytics_parquet_path(
            storage_root, experiment_id, "walk_forward_fold_geometry"
        )
    )

    folds_path = robustness_experiment_analytics_parquet_path(
        storage_root, experiment_id, "walk_forward_folds"
    )
    folds = pl.read_parquet(folds_path)
    stability = compute_walk_forward_stability(experiment_id=experiment_id, folds=folds)
    stability.write_parquet(
        robustness_experiment_analytics_parquet_path(
            storage_root, experiment_id, "walk_forward_stability"
        )
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    backfill_experiment(storage_root=args.storage_root, experiment_id=args.experiment_id)
    print(f"Backfilled {args.experiment_id}: walk_forward_fold_geometry, walk_forward_stability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
