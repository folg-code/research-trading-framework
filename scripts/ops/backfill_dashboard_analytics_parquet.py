"""Backfill Sprint 028 dashboard Parquet analytics under an existing workspace.

Rewrites dual-write Parquet sidecars from already-persisted research artifacts
(JSON analytics / trades+equity). Does not re-run simulations.

    uv run python scripts/ops/backfill_dashboard_analytics_parquet.py
    uv run python scripts/ops/backfill_dashboard_analytics_parquet.py --storage-root user_data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=_REPO_ROOT / "user_data",
        help="Workspace root containing research/",
    )
    return parser


def _backfill_signal_runs(storage_root: Path) -> int:
    from trading_framework.application.signal_research.analytics_envelope import (
        signal_research_analytics_from_dict,
    )
    from trading_framework.application.signal_research.analytics_parquet import (
        require_known_analytics_table_names,
        signal_analytics_parquet_tables,
    )
    from trading_framework.infrastructure.storage.paths import market_research_root
    from trading_framework.research.datasets.signal_research import SignalResearchDatasetRepository

    runs_dir = market_research_root(storage_root) / "runs"
    if not runs_dir.is_dir():
        return 0
    repo = SignalResearchDatasetRepository(storage_root)
    count = 0
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        summary_path = run_dir / "analytics" / "summary.json"
        if not summary_path.is_file():
            continue
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        analytics = signal_research_analytics_from_dict(payload)
        tables = signal_analytics_parquet_tables(analytics)
        require_known_analytics_table_names(tables)
        written = repo.write_analytics_parquet_tables(analytics.source_run_id, tables)
        print(f"signal {analytics.source_run_id}: {len(written)} parquet tables")
        count += 1
    return count


def _backfill_strategy_runs(storage_root: Path) -> int:
    from trading_framework.research.analytics.strategy_dashboard_metrics import (
        compute_strategy_dashboard_analytics,
    )
    from trading_framework.research.analytics.strategy_summary_metrics_export import (
        overview_kpis_to_summary_metrics_frame,
    )
    from trading_framework.research.datasets.strategy_research import (
        StrategyResearchDatasetRepository,
        StrategyResearchRunRef,
    )

    runs_dir = storage_root / "research" / "strategy_research" / "runs"
    if not runs_dir.is_dir():
        return 0
    repo = StrategyResearchDatasetRepository(storage_root)
    count = 0
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        try:
            envelope = repo.read(StrategyResearchRunRef(run_id=run_id))
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"strategy {run_id}: skip ({exc})")
            continue
        dashboard = compute_strategy_dashboard_analytics(
            trades=envelope.trades,
            equity=envelope.equity,
            evaluation_timeframe=envelope.manifest.evaluation_timeframe,
            recent_trade_rows=(),
        )
        frame = overview_kpis_to_summary_metrics_frame(
            run_id=run_id,
            overview=dashboard.overview,
        )
        path = repo.write_summary_metrics(run_id, frame)
        print(f"strategy {run_id}: wrote {path.name}")
        count += 1
    return count


def _backfill_robustness_experiments(storage_root: Path) -> int:
    from trading_framework.research.datasets.robustness import RobustnessExperimentRepository

    experiments_dir = storage_root / "research" / "strategy_robustness" / "experiments"
    if not experiments_dir.is_dir():
        return 0
    repo = RobustnessExperimentRepository(storage_root)
    count = 0
    for exp_dir in sorted(experiments_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        experiment_id = exp_dir.name
        written = 0
        analytics_dir = exp_dir / "analytics"
        try:
            if (analytics_dir / "parameter_sweep.json").is_file():
                repo.write_parameter_sweep_analytics(
                    repo.read_parameter_sweep_analytics(experiment_id)
                )
                written += 1
            if (analytics_dir / "walk_forward.json").is_file():
                repo.write_walk_forward_analytics(repo.read_walk_forward_analytics(experiment_id))
                written += 1
            if (analytics_dir / "stress.json").is_file():
                repo.write_stress_analytics(repo.read_stress_analytics(experiment_id))
                written += 1
            if (analytics_dir / "monte_carlo.json").is_file():
                repo.write_monte_carlo_analytics(repo.read_monte_carlo_analytics(experiment_id))
                written += 1
        except (FileNotFoundError, OSError, ValueError, KeyError, TypeError) as exc:
            print(f"robustness {experiment_id}: skip ({exc})")
            continue
        if written:
            print(f"robustness {experiment_id}: dual-wrote {written} analytics groups")
            count += 1
    return count


def main() -> int:
    args = _build_parser().parse_args()
    storage_root = args.storage_root.expanduser().resolve()
    if not storage_root.is_dir():
        print(f"storage root not found: {storage_root}", file=sys.stderr)
        return 1
    print(f"storage_root={storage_root}")
    signal_n = _backfill_signal_runs(storage_root)
    strategy_n = _backfill_strategy_runs(storage_root)
    robustness_n = _backfill_robustness_experiments(storage_root)
    print(
        f"done: signal_runs={signal_n} strategy_runs={strategy_n} "
        f"robustness_experiments={robustness_n}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
