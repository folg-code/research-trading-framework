"""Backfill Sprint 068 analytics for an existing Strategy Research run.

Phase 18, 18A Milestone 1a (Wave 0 D-P18-01/D-P18-05). For a run persisted
before this sprint: (a) writes real ``SimulationAssumptions`` field values
into its ``manifest.json`` (the fingerprint is left unchanged), and (b)
computes and writes ``analytics/drawdown_episodes.parquet`` and
``analytics/exposure.parquet`` from its already-persisted
``equity.parquet``/``trades.parquet``. No simulator rerun.

    uv run python scripts/strategy_research/backfill_run_analytics.py \\
        --storage-root user_data/workspace --run-id <run_id>

Assumption values default to ``SimulationAssumptions``'s own dataclass
defaults (fill policy ``next_bar_open``/``next_bar_open``, 0 slippage, 0
commission, 100000 initial capital) -- verified in Wave 0 (D-P18-01) to
match all 3 pre-Sprint-068 runs' persisted fingerprint exactly. Override
with the CLI flags below only for a run known to have used different
assumptions.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import polars as pl

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from trading_framework.infrastructure.storage.paths import strategy_research_run_dir  # noqa: E402
from trading_framework.research.analytics.drawdown_episodes import (  # noqa: E402
    compute_drawdown_episodes,
)
from trading_framework.research.analytics.exposure import compute_exposure  # noqa: E402
from trading_framework.research.datasets.strategy_research import (  # noqa: E402
    StrategyResearchDatasetRepository,
    StrategyResearchRunManifest,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fill-policy-entry", default="next_bar_open")
    parser.add_argument("--fill-policy-exit", default="next_bar_open")
    parser.add_argument("--slippage-bps", default="0")
    parser.add_argument("--commission-per-side", default="0")
    parser.add_argument("--initial-capital", default="100000")
    return parser


def backfill_run(
    *,
    storage_root: Path,
    run_id: str,
    fill_policy_entry: str,
    fill_policy_exit: str,
    slippage_bps: str,
    commission_per_side: str,
    initial_capital: str,
) -> None:
    run_dir = strategy_research_run_dir(storage_root, run_id)
    manifest_path = run_dir / "manifest.json"
    manifest = StrategyResearchRunManifest.from_dict(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )
    updated_manifest = dataclasses.replace(
        manifest,
        fill_policy_entry=fill_policy_entry,
        fill_policy_exit=fill_policy_exit,
        slippage_bps=slippage_bps,
        commission_per_side=commission_per_side,
        initial_capital=initial_capital,
    )
    manifest_path.write_text(json.dumps(updated_manifest.to_dict(), indent=2), encoding="utf-8")

    equity = pl.read_parquet(run_dir / "equity.parquet")
    trades = pl.read_parquet(run_dir / "trades.parquet")

    repo = StrategyResearchDatasetRepository(storage_root)
    episodes = compute_drawdown_episodes(run_id=run_id, equity=equity)
    repo.write_drawdown_episodes(run_id, episodes)
    exposure = compute_exposure(run_id=run_id, trades=trades, equity=equity)
    repo.write_exposure(run_id, exposure)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    backfill_run(
        storage_root=args.storage_root,
        run_id=args.run_id,
        fill_policy_entry=args.fill_policy_entry,
        fill_policy_exit=args.fill_policy_exit,
        slippage_bps=args.slippage_bps,
        commission_per_side=args.commission_per_side,
        initial_capital=args.initial_capital,
    )
    print(f"Backfilled {args.run_id}: manifest assumptions, drawdown_episodes, exposure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
