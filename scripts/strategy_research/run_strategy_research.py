"""Run one Strategy Research simulation on a published OHLCV dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import build_canonical_strategy_model
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Strategy Research on a published OHLCV dataset.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root for metadata, datasets and research runs",
    )
    parser.add_argument(
        "--dataset-ref",
        required=True,
        help="Canonical published OHLCV DatasetRef",
    )
    parser.add_argument(
        "--timeframe",
        default="1m",
        help="Dataset and evaluation timeframe (default: 1m)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print run result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the strategy-research CLI."""
    args = _build_parser().parse_args(argv)

    try:
        dataset_ref = DatasetRef.parse(args.dataset_ref)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    timeframe = Timeframe(args.timeframe)
    registry = FileDatasetRegistry(args.storage_root)
    try:
        metadata = registry.get(dataset_ref)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = run_strategy_research(
            RunStrategyResearchRequest(
                dataset_ref=dataset_ref,
                timeframe=timeframe,
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=args.storage_root,
                strategy_model=build_canonical_strategy_model(),
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=timeframe,
                session_resolver=CmeEsRthSessionResolver(),
            )
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "run_id": result.run_id,
        "strategy_model_id": result.manifest.strategy_model_id,
        "trade_count": len(result.trades),
        "equity_points": len(result.equity),
        "simulation_assumptions_fingerprint": result.manifest.simulation_assumptions_fingerprint,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"run_id: {payload['run_id']}")
        print(f"strategy_model_id: {payload['strategy_model_id']}")
        print(f"trade_count: {payload['trade_count']}")
        print(f"equity_points: {payload['equity_points']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
