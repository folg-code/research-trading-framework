"""Backfill Sprint 073 adjusted_forward_drift for an existing Signal Research run.

Phase 18, 18B Milestone 1 (D-P18B-03). Reads the run's already-persisted
``analytics/grouped_summaries.parquet`` and ``analytics/summary_metrics.parquet``
(both produced by ``analyze_signal_research.py --persist-analytics``) and
writes ``analytics/adjusted_forward_drift.parquet`` -- pure post-hoc
computation, no simulator/analysis-engine rerun.

    uv run python scripts/signal_research/backfill_adjusted_drift.py \\
        --storage-root user_data --run-id <run_id>
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
    signal_research_analytics_parquet_path,
)
from trading_framework.research.analytics.adjusted_drift import (  # noqa: E402
    DEFAULT_SHRINKAGE_PRIOR_STRENGTH,
    compute_adjusted_forward_drift,
    empty_adjusted_forward_drift_dataframe,
)


def backfill_run(*, storage_root: Path, run_id: str, prior_strength: int) -> None:
    grouped_summaries_path = signal_research_analytics_parquet_path(
        storage_root, run_id, "grouped_summaries"
    )
    if not grouped_summaries_path.is_file():
        # D-P18B-02: some runs have no grouped_summaries yet (no --definition
        # file authored) -- honestly empty, not an error.
        empty_adjusted_forward_drift_dataframe().write_parquet(
            signal_research_analytics_parquet_path(storage_root, run_id, "adjusted_forward_drift")
        )
        return

    grouped_summaries = pl.read_parquet(grouped_summaries_path)
    summary_metrics = pl.read_parquet(
        signal_research_analytics_parquet_path(storage_root, run_id, "summary_metrics")
    )

    adjusted = compute_adjusted_forward_drift(
        run_id=run_id,
        grouped_summaries=grouped_summaries,
        summary_metrics=summary_metrics,
        prior_strength=prior_strength,
    )
    adjusted.write_parquet(
        signal_research_analytics_parquet_path(storage_root, run_id, "adjusted_forward_drift")
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prior-strength", type=int, default=DEFAULT_SHRINKAGE_PRIOR_STRENGTH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    backfill_run(
        storage_root=args.storage_root, run_id=args.run_id, prior_strength=args.prior_strength
    )
    print(f"Backfilled {args.run_id}: adjusted_forward_drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
