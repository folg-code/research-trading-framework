"""Build a volume-based roll schedule from contract trade datasets."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from trading_framework.application.market_data.build_roll_schedule import (
    BuildRollScheduleRequest,
    build_roll_schedule,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a volume-RTH-close roll schedule from contract trade datasets.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root containing contract trade datasets",
    )
    parser.add_argument(
        "--product",
        required=True,
        help="Root futures product code (e.g. NQ)",
    )
    parser.add_argument(
        "--contract-dataset-ref",
        action="append",
        required=True,
        dest="contract_dataset_refs",
        help="Contract trades DatasetRef (repeatable)",
    )
    parser.add_argument("--start-session", type=_parse_date, default=None)
    parser.add_argument("--end-session", type=_parse_date, default=None)
    parser.add_argument("--confirmation-sessions", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the roll schedule build CLI."""
    args = _build_parser().parse_args(argv)
    try:
        contract_refs = tuple(
            DatasetRef.parse(dataset_ref) for dataset_ref in args.contract_dataset_refs
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = build_roll_schedule(
            BuildRollScheduleRequest(
                storage_root=args.storage_root,
                product=args.product,
                contract_dataset_refs=contract_refs,
                start_session=args.start_session,
                end_session=args.end_session,
                confirmation_sessions=args.confirmation_sessions,
            )
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "product": result.schedule.product,
        "policy_slug": result.schedule.policy.slug,
        "version": result.schedule.version,
        "entry_count": len(result.schedule.entries),
        "start_session": result.manifest.start_session.isoformat(),
        "end_session": result.manifest.end_session.isoformat(),
        "source_fingerprint": result.manifest.source_fingerprint,
        "version_dir": str(result.version_dir),
        "entries": [
            {
                "valid_from_session": entry.valid_from_session.isoformat(),
                "valid_to_session": entry.valid_to_session.isoformat(),
                "active_contract": entry.active_contract,
                "evidence_volume": entry.evidence_volume,
                "roll_id": entry.roll_id,
            }
            for entry in result.schedule.entries
        ],
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"version: {payload['version']}")
        print(f"entries: {payload['entry_count']}")
        print(f"version_dir: {payload['version_dir']}")
        for entry in payload["entries"]:
            print(
                f"  {entry['valid_from_session']}..{entry['valid_to_session']} "
                f"{entry['active_contract']} vol={entry['evidence_volume']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
