"""aiohttp wiring for workbench-api (ADR-0037 section 4: loopback-only JSON API).

Mirrors ``scripts/execution/run_vps_status_service.py``'s pattern: the HTTP
framework lives only here, never in the transport-independent handler
(``datasets_endpoint.py``).
"""

from __future__ import annotations

import asyncio
import signal
from contextlib import suppress

from aiohttp import web

from workbench_core.config import WorkbenchApiConfig
from workbench_core.datasets_endpoint import build_datasets_response

_CONFIG_KEY = web.AppKey("config", WorkbenchApiConfig)


def create_app(config: WorkbenchApiConfig) -> web.Application:
    """Create the aiohttp app exposing the read-only workbench-api."""
    app = web.Application()
    app[_CONFIG_KEY] = config
    app.router.add_get("/api/v1/datasets", _handle_datasets)
    return app


async def _handle_datasets(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    body = build_datasets_response(config)
    return web.json_response(body)


async def run_app(config: WorkbenchApiConfig) -> None:
    """Run workbench-api until interrupted (SIGINT/SIGTERM)."""
    app = create_app(config)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.host, config.port)
    await site.start()
    print(f"Serving workbench-api on http://{config.host}:{config.port}", flush=True)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is not None:
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()
    await runner.cleanup()
