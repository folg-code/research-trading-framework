"""Run a bounded Binance USD-M futures live feed smoke command."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from trading_framework.core.exceptions import TradingFrameworkError, ValidationError
from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesSmokeConfig,
    run_binance_futures_feed_smoke,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded Binance USD-M futures live feed smoke command.",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Binance USD-M futures symbol to stream",
    )
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=10.0,
        help="Maximum wall-clock duration for the smoke run",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=20,
        help="Maximum normalized messages to print",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Binance futures live feed smoke CLI."""
    args = _build_parser().parse_args(argv)
    try:
        config = BinanceFuturesSmokeConfig(
            symbol=args.symbol,
            duration_seconds=args.duration_seconds,
            max_messages=args.max_messages,
        )
        emitted = asyncio.run(
            run_binance_futures_feed_smoke(
                config,
                writer=lambda payload: print(json.dumps(payload, sort_keys=True)),
            )
        )
    except (TradingFrameworkError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps({"event": "summary", "emitted": emitted}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
