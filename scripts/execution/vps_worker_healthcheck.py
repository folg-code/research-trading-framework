"""In-container liveness check for the VPS BTC futures dry-run worker.

Docker ``HEALTHCHECK`` entry point (ADR-0035 section 4.5): the worker has no
HTTP listener, so liveness is heartbeat freshness of its own persisted state,
checked by reading the same execution-state volume the worker itself writes
-- never "process running" alone. This mirrors the staleness pattern already
established by
``trading_framework.application.execution.vps_status_api.handle_vps_execution_status_request``
(T003) instead of inventing a new threshold or classification.

Exit codes:

- ``0`` -- no persisted state yet (startup grace period; the worker has not
  written its first heartbeat) or the persisted heartbeat is fresh.
- ``1`` -- persisted state exists but its heartbeat is stale, or the state is
  unreadable/corrupt (fail closed, matching ADR-0035 section 2.6).

Configuration mirrors the worker's own environment, because this check reads
the same volume the worker writes to:

  TRADING_FRAMEWORK_VPS_STATE_PATH -- base path of the execution-state volume
                                        (default: same as the worker's own
                                        default state path)
  TRADING_FRAMEWORK_VPS_RUNTIME_ID -- runtime id to check (default: same as
                                        the worker's own default runtime id)
  TRADING_FRAMEWORK_VPS_HEALTHCHECK_STALE_AFTER_SECONDS -- freshness
                                        threshold in seconds (default: the
                                        same value as the status API's
                                        ``TRADING_FRAMEWORK_STATUS_STALE_AFTER_SECONDS``
                                        default)
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trading_framework.application.execution.vps_btc_futures_runtime import (
    DEFAULT_VPS_RUNTIME_ID,
    DEFAULT_VPS_STATE_REPOSITORY_PATH,
    VPS_RUNTIME_ENV_PREFIX,
)
from trading_framework.application.execution.vps_status_api import DEFAULT_STALE_AFTER_SECONDS
from trading_framework.core.exceptions import ConfigurationError, TradingFrameworkError
from trading_framework.core.exceptions import ValidationError as TfValidationError
from trading_framework.execution import ExecutionReadModelQuery
from trading_framework.infrastructure.storage.execution_state import (
    JsonExecutionStateRepository,
)

# Mirrors `vps_status_api._UNREADABLE_STATE_ERRORS`: an unreadable/corrupt persisted document is
# fail-closed here too, never treated as "no state" (ADR-0035 section 2.6).
_UNREADABLE_STATE_ERRORS = (
    TradingFrameworkError,
    TfValidationError,
    ValueError,
    KeyError,
    TypeError,
    OSError,
)

# The health check only needs the runtime status envelope (in particular
# `last_heartbeat_at`), not the bounded event/order/fill/bar lists -- request the smallest
# allowed query to avoid parsing work this check does not need.
_MINIMAL_QUERY_LIMIT = 1


def check_worker_is_healthy(env: Mapping[str, str], *, now: datetime) -> bool:
    """Return whether the worker's persisted heartbeat is fresh (or absent, at startup)."""
    state_path = Path(_optional(env, "STATE_PATH", str(DEFAULT_VPS_STATE_REPOSITORY_PATH)))
    runtime_id = _optional(env, "RUNTIME_ID", DEFAULT_VPS_RUNTIME_ID)
    stale_after_seconds = _int(env, "HEALTHCHECK_STALE_AFTER_SECONDS", DEFAULT_STALE_AFTER_SECONDS)

    repository = JsonExecutionStateRepository(state_path)
    query = ExecutionReadModelQuery(
        runtime_id=runtime_id,
        recent_event_limit=_MINIMAL_QUERY_LIMIT,
        recent_order_limit=_MINIMAL_QUERY_LIMIT,
        recent_fill_limit=_MINIMAL_QUERY_LIMIT,
        recent_bar_limit=_MINIMAL_QUERY_LIMIT,
    )
    try:
        view = repository.latest_status_view(query)
    except _UNREADABLE_STATE_ERRORS:
        return False
    if view is None:
        # Startup grace period: the worker has not written its first heartbeat yet. The
        # Dockerfile HEALTHCHECK `start_period` bounds how long this is tolerated.
        return True
    return (now - view.last_heartbeat_at) <= timedelta(seconds=stale_after_seconds)


def main() -> int:
    """Run the health check from environment configuration."""
    try:
        healthy = check_worker_is_healthy(dict(os.environ), now=datetime.now(UTC))
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0 if healthy else 1


def _optional(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(f"{VPS_RUNTIME_ENV_PREFIX}{name}")
    if value is None or not value.strip():
        return default
    return value


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _optional(env, name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{VPS_RUNTIME_ENV_PREFIX}{name} must be an integer") from exc


if __name__ == "__main__":
    raise SystemExit(main())
