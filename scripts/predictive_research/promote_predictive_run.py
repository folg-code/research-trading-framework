"""Promote an existing Predictive Research run into a promoted artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.predictive_research import (
    PromotePredictiveRunRequest,
    promote_predictive_run,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.predictive_run import PredictiveRunRef
from trading_framework.research.predictive.errors import PredictiveSpecError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Promote the last walk-forward fold of one persisted Predictive Research "
            "run into a content-addressed promoted artifact (ADR-0029). Requires the "
            "'ml' extra: promotion reads the run's fitted joblib blob once."
        ),
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Workspace root (contains research/predictive_research/)",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Persisted Predictive Research run_id to promote",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the promotion result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = promote_predictive_run(
            PromotePredictiveRunRequest(
                run_ref=PredictiveRunRef(run_id=args.run_id),
                storage_root=args.storage_root,
            )
        )
    except (ValidationError, PredictiveSpecError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "artifact_fingerprint": result.artifact_fingerprint,
        "directory": str(result.directory),
        "fold_id": result.fold_id,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"artifact_fingerprint: {payload['artifact_fingerprint']}")
        print(f"directory: {payload['directory']}")
        print(f"fold_id: {payload['fold_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
