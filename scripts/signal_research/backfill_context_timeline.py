"""Backfill Sprint 073 context_timeline/persistence for a Signal Research run.

Phase 18, 18B Milestone 1 (D-P18B-04). Recomputes Market Analysis
components over the run's own published dataset by calling the resolved
builder that constructed its Market Model, selects the STATE-kind
components that Market Model actually references (18A's
``state_context_aliases``, D-P18-02), and writes
``analytics/context_timeline.parquet`` and
``analytics/context_persistence.parquet``. Does NOT rerun any Signal
Research evaluation -- only the deterministic, read-only Market Analysis
computation pipeline.

The requested range is derived from the run's own persisted
``occurrences.parquet`` (min/max ``detected_at``) -- the run's own
evaluation window, not the full published dataset's range, which may be
wider than what this run actually evaluated.

    uv run python scripts/signal_research/backfill_context_timeline.py \\
        --storage-root user_data --run-id <run_id> \\
        --market-model-builder "pkg.module:build_market_model"
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
from trading_framework.infrastructure.storage.paths import (  # noqa: E402
    signal_research_analytics_parquet_path,
    signal_research_run_dir,
)
from trading_framework.market.datasets import DatasetRef  # noqa: E402
from trading_framework.market_analysis.models.time_range import TimeRange  # noqa: E402
from trading_framework.market_model.definitions import MarketModelDefinition  # noqa: E402
from trading_framework.model_expression.planning import (  # noqa: E402
    build_analysis_frame_request,
    collect_model_dependencies,
)
from trading_framework.research.analytics.context_timeline import (  # noqa: E402
    compute_context_persistence,
    compute_context_timeline,
)
from trading_framework.time.models.timeframe import Timeframe  # noqa: E402


def _resolve_market_model(market_model_builder: str) -> MarketModelDefinition:
    module_path, _, callable_name = market_model_builder.partition(":")
    if not callable_name:
        msg = f"market_model_builder must be 'module:callable', got {market_model_builder!r}"
        raise ValueError(msg)
    module = importlib.import_module(module_path)
    builder = getattr(module, callable_name)
    market_model: MarketModelDefinition = builder()
    return market_model


def backfill_run(*, storage_root: Path, run_id: str, market_model_builder: str) -> None:
    run_dir = signal_research_run_dir(storage_root, run_id)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    # A run with no signal model (signal_model_ids: []) persists
    # observations.parquet instead of occurrences.parquet -- same
    # detected_at column, different file name for a market-only run.
    occurrences_path = run_dir / "occurrences.parquet"
    if not occurrences_path.is_file():
        occurrences_path = run_dir / "observations.parquet"
    occurrences = pl.read_parquet(occurrences_path)

    market_model = _resolve_market_model(market_model_builder)
    dependencies = collect_model_dependencies(market_models=(market_model,), signal_models=())
    frame_request = build_analysis_frame_request(dependencies)

    dataset_ref = DatasetRef.parse(manifest["source_dataset_ref"])
    evaluation_timeframe = Timeframe(manifest["evaluation_timeframe"])
    requested_range = TimeRange(
        start=occurrences["detected_at"].min(),  # type: ignore[arg-type]
        end=occurrences["detected_at"].max(),  # type: ignore[arg-type]
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

    timeline = compute_context_timeline(
        run_id=run_id, market_model=market_model, frame=result.frame
    )
    persistence = compute_context_persistence(
        run_id=run_id, market_model=market_model, frame=result.frame
    )

    timeline.write_parquet(
        signal_research_analytics_parquet_path(storage_root, run_id, "context_timeline")
    )
    persistence.write_parquet(
        signal_research_analytics_parquet_path(storage_root, run_id, "context_persistence")
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--market-model-builder", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    backfill_run(
        storage_root=args.storage_root,
        run_id=args.run_id,
        market_model_builder=args.market_model_builder,
    )
    print(f"Backfilled {args.run_id}: context_timeline, context_persistence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
