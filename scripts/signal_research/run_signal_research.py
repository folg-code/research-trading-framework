"""Run one Signal Research study from a definition file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.signal_research import (
    map_definition_to_run_request,
    resolve_signal_research_definition,
    run_signal_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.signal_research.loader import load_signal_research_definition
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one Signal Research study from a YAML or JSON definition.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Workspace root (contains market_data/ and research/)",
    )
    parser.add_argument(
        "--definition",
        required=True,
        type=Path,
        help="Path to SignalResearchDefinitionSpec YAML or JSON file",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Evaluate without writing the run envelope to storage",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print run result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spec = load_signal_research_definition(args.definition)
        resolved = resolve_signal_research_definition(spec)
        run_request = map_definition_to_run_request(
            resolved,
            storage_root=args.storage_root,
            session_resolver=CmeEsRthSessionResolver(),
            persist=not args.no_persist,
        )
        result = run_signal_research(run_request)
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "run_id": result.run_id,
        "research_scope": result.manifest.effective_scope().value,
        "source_dataset_ref": result.manifest.source_dataset_ref,
        "signal_model_ids": list(result.manifest.signal_model_ids),
        "market_model_ids": list(result.manifest.market_model_ids),
        "horizon_bars_requested": list(result.manifest.horizon_bars_requested),
        "outcome_rows": len(result.outcomes),
        "persisted": not args.no_persist,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"run_id: {payload['run_id']}")
        print(f"research_scope: {payload['research_scope']}")
        print(f"outcome_rows: {payload['outcome_rows']}")
        print(f"persisted: {payload['persisted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
