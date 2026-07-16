"""Container entry point for the AWS BTCUSDT futures dry-run worker."""

from __future__ import annotations

import json
import os
import sys

from trading_framework.application.execution import (
    JsonCloudWatchExecutionTelemetry,
    load_aws_btc_futures_runtime_config,
    run_aws_btc_futures_dry_run_sync,
)
from trading_framework.core.exceptions import ConfigurationError, TradingFrameworkError


def main() -> int:
    """Run the AWS dry-run worker from environment configuration."""
    try:
        config = load_aws_btc_futures_runtime_config(os.environ)
        telemetry = JsonCloudWatchExecutionTelemetry()
        result = run_aws_btc_futures_dry_run_sync(config, telemetry=telemetry)
    except (ConfigurationError, TradingFrameworkError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "event": "aws_worker_summary",
                "runtime_id": result.runtime.config.runtime_id,
                "symbol": result.runtime.config.symbol,
                "status": result.stopped_status.status.value,
                "aws_region": config.aws_region,
                "execution_state_table": config.execution_state_table_name,
                "execution_state_backend": config.execution_state_backend,
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
