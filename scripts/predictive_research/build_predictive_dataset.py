"""Build one Predictive Research dataset from a study definition."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.predictive.spec import load_predictive_study_spec
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one Predictive Research dataset from a YAML or JSON study.",
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
        help="Path to PredictiveStudySpec YAML or JSON file",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Build without writing the dataset envelope to storage",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print build result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spec = load_predictive_study_spec(args.definition)
        result = build_predictive_dataset(
            BuildPredictiveDatasetRequest(
                spec=spec,
                storage_root=args.storage_root,
                persist=not args.no_persist,
                session_resolver=CmeEsRthSessionResolver(),
            )
        )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "dataset_id": result.dataset_id,
        "dataset_fingerprint": result.fingerprint,
        "definition_hash": result.envelope.manifest.definition_hash,
        "source_dataset_ref": result.envelope.manifest.source_dataset_ref,
        "labelled_rows": result.envelope.manifest.exclusion_counts.get("labelled_rows", 0),
        "feature_rows": len(result.envelope.features),
        "fold_count": result.envelope.manifest.fold_summary.get("fold_count", 0),
        "persisted": result.persisted,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"dataset_id: {payload['dataset_id']}")
        print(f"dataset_fingerprint: {payload['dataset_fingerprint']}")
        print(f"labelled_rows: {payload['labelled_rows']}")
        print(f"feature_rows: {payload['feature_rows']}")
        print(f"persisted: {payload['persisted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
