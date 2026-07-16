"""Print the latest local execution read model as JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.execution import runtime_status_view_to_json
from trading_framework.core.exceptions import TradingFrameworkError, ValidationError
from trading_framework.execution import (
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
)
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository

DEFAULT_STATE_REPOSITORY_PATH = Path("user_data/runtime/btc_futures_dry_run/state")
DEFAULT_RUNTIME_ID = "btc-futures-dry-run-local"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print the latest local execution read model as JSON.",
    )
    parser.add_argument(
        "--state-repository",
        type=Path,
        default=DEFAULT_STATE_REPOSITORY_PATH,
        help="Local JSON execution state repository path",
    )
    parser.add_argument("--runtime-id", default=DEFAULT_RUNTIME_ID)
    parser.add_argument(
        "--recent-events",
        type=int,
        default=DEFAULT_RECENT_EVENT_LIMIT,
        help="Maximum recent execution events to include",
    )
    parser.add_argument(
        "--recent-orders",
        type=int,
        default=DEFAULT_RECENT_ORDER_LIMIT,
        help="Maximum recent simulated orders to include",
    )
    parser.add_argument(
        "--recent-fills",
        type=int,
        default=DEFAULT_RECENT_FILL_LIMIT,
        help="Maximum recent simulated fills to include",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the read-only local execution status CLI."""
    args = _build_parser().parse_args(argv)
    try:
        query = ExecutionReadModelQuery(
            runtime_id=args.runtime_id,
            recent_event_limit=args.recent_events,
            recent_order_limit=args.recent_orders,
            recent_fill_limit=args.recent_fills,
        )
        repository = JsonExecutionStateRepository(args.state_repository)
        status = repository.latest_status_view(query)
    except (TradingFrameworkError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if status is None:
        print(f"no execution status found for runtime_id={query.runtime_id}", file=sys.stderr)
        return 1

    print(json.dumps(runtime_status_view_to_json(status), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
