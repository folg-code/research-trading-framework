"""aiohttp wiring for workbench-api (ADR-0037 section 4: loopback-only JSON API).

Mirrors ``scripts/execution/run_vps_status_service.py``'s pattern: the HTTP
framework lives only here, never in the transport-independent handler
(``datasets_endpoint.py``).
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

from aiohttp import web

from workbench_core.config import WorkbenchApiConfig
from workbench_core.datasets_endpoint import build_datasets_response
from workbench_core.definitions_endpoint import (
    DefinitionRequestError,
    build_list_definitions_response,
    build_load_definition_response,
    build_save_definition_response,
)
from workbench_core.job_runner import (
    DEFAULT_CLI_COMMAND,
    DEFAULT_GRACEFUL_TERMINATION_SECONDS,
    JobCancellationError,
    JobRunner,
    read_job_log,
)
from workbench_core.job_store import JobNotFoundError
from workbench_core.jobs_endpoint import (
    JobRequestError,
    build_cancel_job_response,
    build_get_job_response,
    build_list_jobs_response,
    build_submit_signal_research_job_response,
)
from workbench_core.models_endpoint import build_models_response
from workbench_core.templates_endpoint import (
    TemplateRequestError,
    build_apply_template_response,
    build_templates_response,
)
from workbench_core.validate_endpoint import ValidateRequestError, build_validate_response

_CONFIG_KEY = web.AppKey("config", WorkbenchApiConfig)
_JOB_RUNNER_KEY = web.AppKey("job_runner", JobRunner)
_UI_DIST_DIR_KEY = web.AppKey("ui_dist_dir", Path)

_JOBS_ROOT_NAME = "jobs"
_WORKBENCH_NAMESPACE = "workbench"

#: apps/workbench/src/workbench_core/app.py -> apps/workbench/ui/out
#: (ADR-0044 decision 3/4: `workbench_ui`'s static export, built separately
#: by `npm run build` in apps/workbench/ui/).
_DEFAULT_UI_DIST_DIR = Path(__file__).resolve().parents[2] / "ui" / "out"


def create_app(
    config: WorkbenchApiConfig,
    *,
    cli_command: Sequence[str] | None = None,
    graceful_termination_seconds: float | None = None,
    ui_dist_dir: Path | None = None,
) -> web.Application:
    """Create the aiohttp app exposing workbench-api.

    `cli_command` overrides the spawned `trading-cli` invocation (default
    `("uv", "run", "trading-cli")`) -- a test-only seam so contract tests can
    substitute a stub child process instead of a real `uv run` (JobRunner's
    own docstring explains why the subprocess itself is never faked
    in-process). `graceful_termination_seconds` overrides D-S064-03's default
    20s grace window -- also test-only, so a cancellation contract test does
    not need a 20s+ budget just to observe a hard-kill escalation.
    `ui_dist_dir` overrides where the built `workbench_ui` static export is
    served from (default `apps/workbench/ui/out`) -- a test-only seam so
    contract tests do not depend on a real `npm run build` having run.
    """
    app = web.Application()
    app[_CONFIG_KEY] = config
    app[_UI_DIST_DIR_KEY] = ui_dist_dir if ui_dist_dir is not None else _DEFAULT_UI_DIST_DIR
    jobs_root = config.storage_root / _WORKBENCH_NAMESPACE / _JOBS_ROOT_NAME
    app[_JOB_RUNNER_KEY] = JobRunner(
        jobs_root=jobs_root,
        storage_root=config.storage_root,
        cli_command=cli_command if cli_command is not None else DEFAULT_CLI_COMMAND,
        graceful_termination_seconds=(
            graceful_termination_seconds
            if graceful_termination_seconds is not None
            else DEFAULT_GRACEFUL_TERMINATION_SECONDS
        ),
    )
    app.router.add_get("/api/v1/datasets", _handle_datasets)
    app.router.add_get("/api/v1/templates", _handle_templates)
    app.router.add_get("/api/v1/models", _handle_models)
    app.router.add_post("/api/v1/templates/{template_id}/apply", _handle_apply_template)
    app.router.add_post("/api/v1/validate", _handle_validate)
    app.router.add_get("/api/v1/definitions", _handle_list_definitions)
    app.router.add_post("/api/v1/definitions", _handle_save_definition)
    app.router.add_get("/api/v1/definitions/{name}", _handle_load_definition)
    app.router.add_post("/api/v1/jobs", _handle_submit_job)
    app.router.add_get("/api/v1/jobs", _handle_list_jobs)
    app.router.add_get("/api/v1/jobs/{job_id}", _handle_get_job)
    app.router.add_get("/api/v1/jobs/{job_id}/log", _handle_get_job_log)
    app.router.add_post("/api/v1/jobs/{job_id}/cancel", _handle_cancel_job)
    # Registered last: aiohttp's UrlDispatcher tries resources in the order
    # they were added, so every /api/v1/* route above is matched first --
    # this catch-all only ever serves the static workbench_ui build.
    app.router.add_get("/{path:.*}", _handle_static)
    app.on_startup.append(_start_job_runner)
    app.on_cleanup.append(_stop_job_runner)
    return app


async def _handle_datasets(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    body = build_datasets_response(config)
    return web.json_response(body)


async def _handle_templates(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    return web.json_response(build_templates_response(config))


async def _handle_models(request: web.Request) -> web.Response:
    del request
    return web.json_response(build_models_response())


async def _handle_apply_template(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "request body must be JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "request body must be a JSON object"}, status=400)
    try:
        payload = build_apply_template_response(config, request.match_info["template_id"], body)
    except TemplateRequestError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    return web.json_response(payload)


async def _handle_validate(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "request body must be JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "request body must be a JSON object"}, status=400)
    try:
        payload = await build_validate_response(config, body)
    except ValidateRequestError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    return web.json_response(payload)


async def _handle_list_definitions(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    return web.json_response(build_list_definitions_response(config))


async def _handle_save_definition(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "request body must be JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "request body must be a JSON object"}, status=400)
    try:
        payload = build_save_definition_response(config, body)
    except DefinitionRequestError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    return web.json_response(payload, status=201)


async def _handle_load_definition(request: web.Request) -> web.Response:
    config = request.app[_CONFIG_KEY]
    try:
        payload = build_load_definition_response(config, request.match_info["name"])
    except DefinitionRequestError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    return web.json_response(payload)


async def _handle_submit_job(request: web.Request) -> web.Response:
    runner = request.app[_JOB_RUNNER_KEY]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "request body must be JSON"}, status=400)
    if not isinstance(body, dict):
        return web.json_response({"error": "request body must be a JSON object"}, status=400)
    try:
        payload = build_submit_signal_research_job_response(runner, body)
    except JobRequestError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    return web.json_response(payload, status=201)


async def _handle_get_job(request: web.Request) -> web.Response:
    runner = request.app[_JOB_RUNNER_KEY]
    try:
        payload = build_get_job_response(runner, request.match_info["job_id"])
    except JobRequestError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    return web.json_response(payload)


async def _handle_list_jobs(request: web.Request) -> web.Response:
    runner = request.app[_JOB_RUNNER_KEY]
    return web.json_response(build_list_jobs_response(runner))


async def _handle_get_job_log(request: web.Request) -> web.Response:
    runner = request.app[_JOB_RUNNER_KEY]
    job_id = request.match_info["job_id"]
    try:
        runner.get_job(job_id)
    except JobNotFoundError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    config = request.app[_CONFIG_KEY]
    jobs_root = config.storage_root / _WORKBENCH_NAMESPACE / _JOBS_ROOT_NAME
    stdout = read_job_log(jobs_root, job_id)
    return web.json_response({"job_id": job_id, "stdout": stdout})


async def _handle_cancel_job(request: web.Request) -> web.Response:
    runner = request.app[_JOB_RUNNER_KEY]
    try:
        payload = build_cancel_job_response(runner, request.match_info["job_id"])
    except JobNotFoundError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    except JobCancellationError as exc:
        return web.json_response({"error": str(exc)}, status=409)
    return web.json_response(payload)


async def _handle_static(request: web.Request) -> web.StreamResponse:
    """Serve `workbench_ui`'s static export (ADR-0044 decisions 2/3): no
    Next.js server, no API routes -- `workbench-api` is the only thing
    serving this build, over plain files."""
    ui_dist_dir = request.app[_UI_DIST_DIR_KEY]
    if not ui_dist_dir.is_dir():
        return web.Response(
            status=404,
            text=(
                "workbench_ui build not found at "
                f"{ui_dist_dir} -- run `npm run build` in apps/workbench/ui first"
            ),
        )
    candidate = _resolve_static_file(ui_dist_dir, request.match_info["path"])
    if candidate is None:
        return web.Response(status=404, text="not found")
    return web.FileResponse(candidate)


def _resolve_static_file(dist_dir: Path, requested_path: str) -> Path | None:
    resolved_root = dist_dir.resolve()
    candidate = (dist_dir / requested_path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None  # path traversal attempt (e.g. "../../etc/passwd")
    if candidate.is_file():
        return candidate
    # Next.js static export with the default trailingSlash: false renders a
    # route with no extension to "<route>.html" (e.g. GET /jobs -> jobs.html)
    # rather than "<route>/index.html".
    html_candidate = (
        dist_dir / "index.html" if not requested_path else dist_dir / f"{requested_path}.html"
    )
    return html_candidate if html_candidate.is_file() else None


async def _start_job_runner(app: web.Application) -> None:
    app[_JOB_RUNNER_KEY].start()


async def _stop_job_runner(app: web.Application) -> None:
    await app[_JOB_RUNNER_KEY].stop()


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
