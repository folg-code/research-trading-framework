"""Serve the read-only VPS BTC futures dry-run status API (aiohttp).

Implements the GET-only ``execution.status.v1`` contract frozen in
``docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md``. This process only reads the
shared execution-state volume through ``JsonExecutionStateRepository`` / ``ExecutionStateReader``
and never writes it. Per the ADR it is Compose-``expose``-only: not published to a host port and
not reachable from the internet, with the dashboard as its only caller.

Routes:
  GET /status   -- the versioned, sanitized, allowlisted snapshot (section 3).
  GET /healthz  -- process liveness + state-volume readability only (section 4.5).

Configuration is environment-only; no AWS-specific value is required (D062-02):
  TRADING_FRAMEWORK_STATUS_STATE_PATH          -- base path of the execution-state volume
                                                   (required)
  TRADING_FRAMEWORK_STATUS_RUNTIME_ID          -- runtime id to serve
                                                   (default: btc-futures-dry-run-vps)
  TRADING_FRAMEWORK_STATUS_STALE_AFTER_SECONDS -- freshness threshold in seconds (default: 120)
  TRADING_FRAMEWORK_STATUS_RECENT_EVENTS/ORDERS/FILLS/BARS -- bounded list sizes
  TRADING_FRAMEWORK_STATUS_HOST                -- bind host (default: 0.0.0.0)
  TRADING_FRAMEWORK_STATUS_PORT                -- bind port (default: 8090)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, final

from aiohttp import web

from trading_framework.application.execution import (
    VpsExecutionStatusApiConfig,
    handle_vps_execution_status_request,
    handle_vps_status_health_check,
    load_vps_execution_status_api_config,
)
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.execution import ExecutionStateReader
from trading_framework.infrastructure.storage.execution_state import (
    JsonExecutionStateRepository,
)

DEFAULT_HOST: Final = "0.0.0.0"
DEFAULT_PORT: Final = 8090
STATE_PATH_ENV: Final = "TRADING_FRAMEWORK_STATUS_STATE_PATH"

_CONFIG_KEY = web.AppKey("config", VpsExecutionStatusApiConfig)
_REPOSITORY_KEY = web.AppKey("repository", ExecutionStateReader)


@final
@dataclass(frozen=True, slots=True)
class ServiceRuntimeConfig:
    """Bind address and status-API configuration for the running process."""

    host: str
    port: int
    api_config: VpsExecutionStatusApiConfig
    state_repository: JsonExecutionStateRepository


def load_service_runtime_config(env: dict[str, str]) -> ServiceRuntimeConfig:
    """Load bind address, state path and the status API config from the environment."""
    state_path_raw = env.get(STATE_PATH_ENV, "").strip()
    if not state_path_raw:
        raise ConfigurationError(f"{STATE_PATH_ENV} is required")
    return ServiceRuntimeConfig(
        host=env.get("TRADING_FRAMEWORK_STATUS_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST,
        port=_int(env, "TRADING_FRAMEWORK_STATUS_PORT", DEFAULT_PORT),
        api_config=load_vps_execution_status_api_config(env),
        state_repository=JsonExecutionStateRepository(Path(state_path_raw)),
    )


def create_app(config: ServiceRuntimeConfig) -> web.Application:
    """Create the aiohttp app exposing /status and /healthz."""
    app = web.Application()
    app[_CONFIG_KEY] = config.api_config
    app[_REPOSITORY_KEY] = config.state_repository
    # "*" so non-GET methods reach our own handler (which returns the documented 405 + Allow:
    # GET JSON body) instead of aiohttp's default plain-text 405 for an unregistered method.
    app.router.add_route("*", "/status", _handle_status)
    app.router.add_get("/healthz", _handle_health)
    return app


async def _handle_status(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    repository = request.app[_REPOSITORY_KEY]
    response = handle_vps_execution_status_request(
        request.method,
        config=config,
        repository=repository,
        now=datetime.now(UTC),
    )
    return _json_response(response.status_code, response.headers, response.body)


async def _handle_health(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    repository = request.app[_REPOSITORY_KEY]
    response = handle_vps_status_health_check(repository=repository, config=config)
    return _json_response(response.status_code, response.headers, response.body)


def _json_response(
    status_code: int,
    headers: Mapping[str, str],
    body: Mapping[str, object],
) -> web.Response:
    """Build a JSON response without clashing aiohttp's own Content-Type handling."""
    remaining_headers = {
        key: value for key, value in headers.items() if key.lower() != "content-type"
    }
    return web.json_response(dict(body), status=status_code, headers=remaining_headers)


def _int(env: dict[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve the read-only VPS BTC futures dry-run status API.",
    )
    parser.add_argument("--host", default=None, help="Overrides TRADING_FRAMEWORK_STATUS_HOST")
    parser.add_argument(
        "--port", type=int, default=None, help="Overrides TRADING_FRAMEWORK_STATUS_PORT"
    )
    return parser


async def _run_app(host: str, port: int, app: web.Application) -> None:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"Serving VPS dry-run status API on http://{host}:{port}", flush=True)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is not None:
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await runner.cleanup()


def main(argv: list[str] | None = None) -> int:
    """Run the VPS status service until interrupted."""
    args = _build_parser().parse_args(argv)
    try:
        runtime_config = load_service_runtime_config(dict(os.environ))
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    host = args.host or runtime_config.host
    port = args.port or runtime_config.port
    asyncio.run(_run_app(host, port, create_app(runtime_config)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
