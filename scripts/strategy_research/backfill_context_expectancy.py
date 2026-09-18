"""Backfill Sprint 069 context_expectancy for an existing Strategy Research run.

Phase 18, 18A Milestone 1b (Wave 0 D-P18-02). For a run persisted before
this sprint: recomputes Market Analysis components over the run's own
published dataset by calling the resolved builder that originally
constructed its Market Model, selects the STATE-kind components that
Market Model actually references, joins them to the run's already-
persisted trades.parquet at entry_signal_at, and writes
analytics/context_expectancy.parquet. Also backfills the manifest's new
strategy_source_ref field with the resolved builder path, so a future pass
never needs to re-resolve it by hand.

This recomputes Market Analysis components (deterministic, read-only) --
it does NOT rerun BarSequentialSimulator.

    uv run python scripts/strategy_research/backfill_context_expectancy.py \\
        --storage-root user_data/workspace --run-id <run_id> \\
        --strategy-source-ref "pkg.module:build_strategy"
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import polars as pl

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from trading_framework.application.market_analysis.run_analysis import (  # noqa: E402
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.infrastructure.storage.paths import strategy_research_run_dir  # noqa: E402
from trading_framework.market.datasets import DatasetRef  # noqa: E402
from trading_framework.market_analysis.models.time_range import TimeRange  # noqa: E402
from trading_framework.market_model.definitions import MarketModelDefinition  # noqa: E402
from trading_framework.model_expression.planning import (  # noqa: E402
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.research.analytics.context_expectancy import (  # noqa: E402
    compute_context_expectancy,
)
from trading_framework.research.datasets.strategy_research import (  # noqa: E402
    StrategyResearchDatasetRepository,
    StrategyResearchRunManifest,
)
from trading_framework.time.models.timeframe import Timeframe  # noqa: E402


def _resolve_market_model(strategy_source_ref: str) -> MarketModelDefinition:
    module_path, _, callable_name = strategy_source_ref.partition(":")
    if not callable_name:
        msg = f"strategy_source_ref must be 'module:callable', got {strategy_source_ref!r}"
        raise ValueError(msg)
    module = importlib.import_module(module_path)
    builder = getattr(module, callable_name)
    strategy_model = builder()
    market_model: MarketModelDefinition = strategy_model.market_model
    return market_model


def backfill_run(*, storage_root: Path, run_id: str, strategy_source_ref: str) -> None:
    run_dir = strategy_research_run_dir(storage_root, run_id)
    manifest = StrategyResearchRunManifest.from_dict(
        json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    )
    trades = pl.read_parquet(run_dir / "trades.parquet")
    equity = pl.read_parquet(run_dir / "equity.parquet")

    market_model = _resolve_market_model(strategy_source_ref)
    dependencies = collect_model_dependencies(market_models=(market_model,), signal_models=())
    frame_request = build_analysis_frame_request(dependencies)

    dataset_ref = DatasetRef.parse(manifest.source_dataset_ref)
    evaluation_timeframe = Timeframe(manifest.evaluation_timeframe)
    requested_range = TimeRange(
        start=equity["observed_at"].min(),  # type: ignore[arg-type]
        end=equity["observed_at"].max(),  # type: ignore[arg-type]
    )

    result = run_analysis(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=dataset_ref.dataset_id.timeframe,
            requested_range=requested_range,
            storage_root=storage_root,
            component_requests=dependencies.component_requests,
            frame_request=frame_request,
            evaluation_timeframe=evaluation_timeframe,
        )
    )
    if result.frame is None:
        msg = "run_analysis did not assemble a frame"
        raise RuntimeError(msg)

    context_expectancy = compute_context_expectancy(
        run_id=run_id,
        market_model=market_model,
        frame=result.frame,
        trades=trades,
    )

    repo = StrategyResearchDatasetRepository(storage_root)
    repo.write_context_expectancy(run_id, context_expectancy)
    repo.update_strategy_source_ref(run_id, strategy_source_ref)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--strategy-source-ref", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    backfill_run(
        storage_root=args.storage_root,
        run_id=args.run_id,
        strategy_source_ref=args.strategy_source_ref,
    )
    print(f"Backfilled {args.run_id}: context_expectancy, strategy_source_ref.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
