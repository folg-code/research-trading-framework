"""`trading-cli dry-run start` (S046-T008).

Wraps ``run_local_btc_futures_binance_dry_run`` unmodified -- no execution
logic changes. **Event-loop entry (SPRINT_046.md Sec4 finding 4):** the
wrapped application call is ``async`` and the existing script drives it with
``asyncio.run()``. ``trading_cli.cli.main`` is itself synchronous top-level
code (argparse -> dispatch -> return), so `main()` is never already inside a
running event loop when this module's ``run()`` calls ``asyncio.run()`` --
this mirrors the script exactly and needs no extra guard.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesBinanceDryRunRequest,
    run_local_btc_futures_binance_dry_run,
)
from trading_framework.core.exceptions import TradingFrameworkError, ValidationError

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
from trading_cli.plan import ResolvedPlan

_DEFAULT_EVENT_LOG_PATH = Path("user_data/runtime/btc_futures_dry_run/events.jsonl")
_DEFAULT_HEARTBEAT_SECONDS = 30.0


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.dry_run is None:
        raise ConfigError("config is missing the 'dry_run' block required by 'dry-run start'")
    args = dict(config.dry_run)
    if "duration_minutes" not in args:
        raise ConfigError(
            "config is missing 'dry_run.duration_minutes' required by 'dry-run start'"
        )
    event_log = args.get("event_log") or str(_DEFAULT_EVENT_LOG_PATH)
    return ResolvedPlan(
        group="dry-run",
        command="start",
        workflow="dry_run.start",
        arguments={**args, "event_log": event_log},
        output_paths=(str(event_log),),
        storage_root=str(config.storage_root),
        implemented=True,
    )


def run(plan: ResolvedPlan) -> dict[str, Any]:
    duration_minutes_raw = plan.arguments["duration_minutes"]
    try:
        duration_minutes = float(duration_minutes_raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"invalid 'dry_run.duration_minutes': {duration_minutes_raw!r}") from exc
    if duration_minutes <= 0:
        raise ConfigError("'dry_run.duration_minutes' must be positive")

    symbol = str(plan.arguments.get("symbol") or "BTCUSDT")
    event_log = Path(plan.arguments["event_log"])

    try:
        result = asyncio.run(
            run_local_btc_futures_binance_dry_run(
                RunLocalBtcFuturesBinanceDryRunRequest(
                    config=LocalBtcFuturesDryRunConfig(
                        event_log_path=event_log,
                        symbol=symbol,
                        starting_equity=Decimal("10000"),
                    ),
                    duration_seconds=duration_minutes * 60,
                    heartbeat_seconds=_DEFAULT_HEARTBEAT_SECONDS,
                )
            )
        )
    except (TradingFrameworkError, ValidationError) as exc:
        raise WorkflowError(f"'dry-run start' failed: {exc}") from exc

    return {
        "runtime_id": result.runtime.config.runtime_id,
        "symbol": result.runtime.config.symbol,
        "status": result.stopped_status.status.value,
        "event_log": str(result.runtime.config.event_log_path),
        "received_messages": result.received_message_count,
        "closed_bars": result.feed_state.closed_bar_count,
    }
