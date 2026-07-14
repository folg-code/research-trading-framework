"""Build continuous futures trades and derived OHLCV in one preprocessing command."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from trading_framework.application.market_data.build_continuous import (
    BuildContinuousRequest,
    build_continuous,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.market.continuous.policy import VOLUME_RTH_CLOSE_POLICY_SLUG
from trading_framework.market.datasets import DatasetRef


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build roll schedule, continuous trades and derived OHLCV for one futures product."
        ),
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
    parser.add_argument(
        "--roll-policy",
        default=VOLUME_RTH_CLOSE_POLICY_SLUG,
        help="Roll policy slug (MVP: volume-rth-close)",
    )
    parser.add_argument("--start-session", type=_parse_date, default=None)
    parser.add_argument("--end-session", type=_parse_date, default=None)
    parser.add_argument("--confirmation-sessions", type=int, default=1)
    parser.add_argument("--rebuild-all", action="store_true")
    parser.add_argument("--rebuild-window-sessions", type=int, default=10)
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Leave outputs in WORKING/FINALIZED state without publishing",
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the continuous futures build CLI."""
    args = _build_parser().parse_args(argv)
    try:
        contract_refs = tuple(
            DatasetRef.parse(dataset_ref) for dataset_ref in args.contract_dataset_refs
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = build_continuous(
            BuildContinuousRequest(
                storage_root=args.storage_root,
                product=args.product,
                contract_dataset_refs=contract_refs,
                policy_slug=args.roll_policy,
                start_session=args.start_session,
                end_session=args.end_session,
                confirmation_sessions=args.confirmation_sessions,
                rebuild_all=args.rebuild_all,
                rebuild_window_sessions=args.rebuild_window_sessions,
                publish=not args.no_publish,
            )
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "roll_schedule_version": result.roll_schedule_version,
        "continuous_trades_dataset_ref": str(result.continuous_trades_dataset_ref),
        "continuous_ohlcv_dataset_ref": str(result.continuous_ohlcv_dataset_ref),
        "trades_reused": result.trades_reused,
        "ohlcv_reused": result.ohlcv_reused,
        "published_trades": result.published_trades,
        "published_ohlcv": result.published_ohlcv,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"roll_schedule_version: {payload['roll_schedule_version']}")
        print(f"continuous_trades_dataset_ref: {payload['continuous_trades_dataset_ref']}")
        print(f"continuous_ohlcv_dataset_ref: {payload['continuous_ohlcv_dataset_ref']}")
        print(f"trades_reused: {payload['trades_reused']}")
        print(f"ohlcv_reused: {payload['ohlcv_reused']}")
        print(f"published_trades: {payload['published_trades']}")
        print(f"published_ohlcv: {payload['published_ohlcv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
