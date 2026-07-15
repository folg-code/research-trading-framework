"""Run a bounded local BTCUSDT futures dry-run lifecycle."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesBinanceDryRunRequest,
    run_local_btc_futures_binance_dry_run,
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
        help="Maximum bounded live dry-run duration in minutes",
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
    parser.add_argument(
        "--max-closed-bars",
        type=int,
        default=200,
        help="Maximum rolling closed 1m bars retained for live signal evaluation",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=None,
        help="Optional maximum Binance messages to process before stopping",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local BTC futures dry-run CLI."""
    args = _build_parser().parse_args(argv)
    try:
        if args.duration_minutes <= 0:
            msg = "duration_minutes must be positive"
            raise ValidationError(msg)
        strategy_config = BtcFuturesDemoStrategyConfig(
            ema_period=args.ema_period,
            exit_after_bars=args.exit_after_bars,
            quantity=args.quantity,
        )
        result = asyncio.run(
            run_local_btc_futures_binance_dry_run(
                RunLocalBtcFuturesBinanceDryRunRequest(
                    config=LocalBtcFuturesDryRunConfig(
                        event_log_path=args.event_log,
                        runtime_id=args.runtime_id,
                        symbol=args.symbol,
                        starting_equity=args.starting_equity,
                        strategy_config=strategy_config,
                    ),
                    duration_seconds=args.duration_minutes * 60,
                    heartbeat_seconds=args.heartbeat_seconds,
                    max_closed_bars=args.max_closed_bars,
                    max_messages=args.max_messages,
                )
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
                "received_messages": result.received_message_count,
                "closed_bars": result.feed_state.closed_bar_count,
                "ignored_messages": result.feed_state.ignored_message_count,
                "simulated": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
