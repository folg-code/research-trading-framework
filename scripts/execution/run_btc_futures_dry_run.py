"""Run a bounded local BTCUSDT futures dry-run lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesDryRunRequest,
    run_local_btc_futures_dry_run,
)
from trading_framework.core.exceptions import TradingFrameworkError, ValidationError
from trading_framework.strategy import BtcFuturesDemoStrategyConfig

DEFAULT_EVENT_LOG_PATH = Path("user_data/runtime/btc_futures_dry_run/events.jsonl")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded local BTCUSDT futures dry-run lifecycle.",
    )
    parser.add_argument(
        "--event-log",
        type=Path,
        default=DEFAULT_EVENT_LOG_PATH,
        help="JSONL path for local dry-run execution events",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=1.0,
        help="Maximum bounded runtime duration in minutes",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=30.0,
        help="Heartbeat interval during the bounded local run",
    )
    parser.add_argument("--runtime-id", default="btc-futures-dry-run-local")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--starting-equity", type=Decimal, default=Decimal("10000"))
    parser.add_argument("--quantity", type=Decimal, default=Decimal("0.001"))
    parser.add_argument("--ema-period", type=int, default=20)
    parser.add_argument("--exit-after-bars", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local BTC futures dry-run CLI."""
    args = _build_parser().parse_args(argv)
    try:
        strategy_config = BtcFuturesDemoStrategyConfig(
            ema_period=args.ema_period,
            exit_after_bars=args.exit_after_bars,
            quantity=args.quantity,
        )
        result = run_local_btc_futures_dry_run(
            RunLocalBtcFuturesDryRunRequest(
                config=LocalBtcFuturesDryRunConfig(
                    event_log_path=args.event_log,
                    runtime_id=args.runtime_id,
                    symbol=args.symbol,
                    starting_equity=args.starting_equity,
                    strategy_config=strategy_config,
                ),
                duration_minutes=args.duration_minutes,
                heartbeat_seconds=args.heartbeat_seconds,
            )
        )
    except (TradingFrameworkError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "event": "summary",
                "runtime_id": result.runtime.config.runtime_id,
                "symbol": result.runtime.config.symbol,
                "status": result.stopped_status.status.value,
                "event_log": str(result.runtime.config.event_log_path),
                "simulated": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
