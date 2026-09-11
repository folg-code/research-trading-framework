"""Container entry point for the VPS BTCUSDT futures dry-run worker.

Provider-neutral (ADR-0036 D062-02): unlike
``scripts/execution/run_aws_btc_futures_worker.py``, this entry point never
requires an AWS-specific environment value and defaults to a continuous
service lifetime rather than a bounded one-hour task.

Exit codes:

- ``0`` -- graceful stop (SIGTERM/SIGINT) or a bounded smoke run completed.
- ``1`` -- configuration error or unrecoverable runtime failure.
- ``2`` -- refuse-to-start: persisted execution state is incompatible with
  the current configuration or is unreadable/incomplete (ADR-0036 SS4.4).
  Deliberately discarding paper state is an explicit operator action; it is
  never automatic.
"""

from __future__ import annotations

import json
import os
import sys

from trading_framework.application.execution.vps_btc_futures_runtime import (
    load_vps_btc_futures_runtime_config,
    run_vps_btc_futures_dry_run_sync,
)
from trading_framework.core.exceptions import (
    ConfigurationError,
    IncompatibleExecutionStateError,
    TradingFrameworkError,
)


def main() -> int:
    """Run the VPS dry-run worker from environment configuration."""
    try:
        config = load_vps_btc_futures_runtime_config(os.environ)
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = run_vps_btc_futures_dry_run_sync(config)
    except IncompatibleExecutionStateError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except TradingFrameworkError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # last-resort unrecoverable-failure boundary
        # The reused runtime loop already persisted FAILED (best-effort) and
        # re-raised whatever it caught, which need not be a
        # TradingFrameworkError (e.g. a feed/network/OS error). Report a
        # single-line message here instead of letting an uncaught traceback
        # print unbounded internal detail, including container-local
        # absolute paths, to stderr (ADR-0036 SS4.7).
        print(f"unrecoverable worker failure: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "event": "vps_worker_summary",
                "runtime_id": result.runtime.config.runtime_id,
                "symbol": result.runtime.config.symbol,
                "status": result.stopped_status.status.value,
                "continuous": config.is_continuous,
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
