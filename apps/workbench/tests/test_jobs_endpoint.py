"""HTTP contract tests for the job submit/get/list/log/cancel endpoints
(Sprint 064 T006/T007).

Same pattern as `test_datasets_endpoint.py`: `aiohttp.test_utils`, no
`pytest-asyncio` dependency, a real (stub) child process rather than an
in-process fake -- ADR-0041 section 2 forbids `workbench_core` calling a
research workflow in-process for a job.
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.job_store import JobState
from workbench_core.windows_process import IS_WINDOWS

_LONG_RUNNING_CHILD = textwrap.dedent(
    """
    import time
    print("running", flush=True)
    time.sleep(30)
    """
)

_SUCCEEDING_CHILD = textwrap.dedent(
    """
    import json
    import sys

    for index, name in enumerate(["load-definition", "resolve-models"], start=1):
        print(json.dumps({"event": "phase", "name": name, "index": index, "of": 2}))
    print(json.dumps({"status": "success", "result": {"run_id": "synthetic-run"}}))
    sys.exit(0)
    """
)


def _write_stub(
    tmp_path: Path, name: str = "succeeding_child.py", script: str = _SUCCEEDING_CHILD
) -> tuple[str, ...]:
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    return (sys.executable, str(path))


def test_job_submit_get_list_and_log_contract(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config, cli_command=cli_command)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            submit_response = await client.post(
                "/api/v1/jobs", json={"definition_path": "signal_definition.yaml"}
            )
            assert submit_response.status == 201
            submitted = await submit_response.json()
            assert submitted["job_kind"] == "research.run.signal"
            assert submitted["state"] == JobState.QUEUED.value
            job_id = submitted["job_id"]

            # the background worker races the test; poll get_job for a
            # terminal state instead of sleeping a fixed amount.
            final_state = None
            for _attempt in range(200):
                get_response = await client.get(f"/api/v1/jobs/{job_id}")
                assert get_response.status == 200
                payload = await get_response.json()
                if payload["state"] in (JobState.SUCCEEDED.value, JobState.FAILED.value):
                    final_state = payload
                    break
                await asyncio.sleep(0.02)
            assert final_state is not None, "job did not reach a terminal state in time"
            assert final_state["state"] == JobState.SUCCEEDED.value
            assert final_state["exit_code"] == 0
            assert final_state["config_path"]
            assert final_state["latest_phase"]["name"] == "resolve-models"

            list_response = await client.get("/api/v1/jobs")
            assert list_response.status == 200
            listed = await list_response.json()
            assert [job["job_id"] for job in listed["jobs"]] == [job_id]

            log_response = await client.get(f"/api/v1/jobs/{job_id}/log")
            assert log_response.status == 200
            log_payload = await log_response.json()
            assert '"name": "load-definition"' in log_payload["stdout"]
            assert '"run_id": "synthetic-run"' in log_payload["stdout"]
        finally:
            await client.close()

    asyncio.run(_run())


def test_get_unknown_job_is_404(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.get("/api/v1/jobs/does-not-exist")
            assert response.status == 404
        finally:
            await client.close()

    asyncio.run(_run())


def test_submit_job_missing_definition_path_is_400(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/v1/jobs", json={})
            assert response.status == 400
        finally:
            await client.close()

    asyncio.run(_run())


def test_cancel_unknown_job_is_404(tmp_path: Path) -> None:
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            response = await client.post("/api/v1/jobs/does-not-exist/cancel")
            assert response.status == 404
        finally:
            await client.close()

    asyncio.run(_run())


def test_cancel_already_succeeded_job_is_409(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path)
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        app = create_app(config, cli_command=cli_command)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            submit_response = await client.post(
                "/api/v1/jobs", json={"definition_path": "signal_definition.yaml"}
            )
            job_id = (await submit_response.json())["job_id"]
            for _attempt in range(200):
                payload = await (await client.get(f"/api/v1/jobs/{job_id}")).json()
                if payload["state"] == JobState.SUCCEEDED.value:
                    break
                await asyncio.sleep(0.02)
            else:
                pytest.fail("job did not reach SUCCEEDED in time")

            cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
            assert cancel_response.status == 409
        finally:
            await client.close()

    asyncio.run(_run())


@pytest.mark.skipif(
    not IS_WINDOWS, reason="process-tree cancellation is Windows-only this sprint (ADR-0041 §6)"
)
def test_cancel_running_job_via_http(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path, "long_running_child.py", _LONG_RUNNING_CHILD)
    config = WorkbenchApiConfig(storage_root=tmp_path)

    async def _run() -> None:
        # A short, explicit grace window with real margin under this test's
        # own ~10s polling budget below -- and, before cancelling, waiting
        # for the child's own first print rather than just JobState.RUNNING
        # (which only means the OS process object exists): a CTRL_BREAK sent
        # the instant the process object exists, before its new process
        # group has finished setting up, can be silently dropped.
        app = create_app(config, cli_command=cli_command, graceful_termination_seconds=3.0)
        client = TestClient(TestServer(app))
        await client.start_server()
        try:
            submit_response = await client.post(
                "/api/v1/jobs", json={"definition_path": "signal_definition.yaml"}
            )
            job_id = (await submit_response.json())["job_id"]
            for _attempt in range(200):
                payload = await (await client.get(f"/api/v1/jobs/{job_id}")).json()
                if payload["state"] == JobState.RUNNING.value:
                    break
                await asyncio.sleep(0.02)
            else:
                pytest.fail("job did not reach RUNNING in time")

            for _attempt in range(200):
                log_payload = await (await client.get(f"/api/v1/jobs/{job_id}/log")).json()
                if "running" in log_payload["stdout"]:
                    break
                await asyncio.sleep(0.02)
            else:
                pytest.fail("child's readiness line never appeared in the log in time")

            cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
            assert cancel_response.status == 200

            final_state = None
            for _attempt in range(500):
                payload = await (await client.get(f"/api/v1/jobs/{job_id}")).json()
                if payload["state"] == JobState.CANCELLED.value:
                    final_state = payload
                    break
                await asyncio.sleep(0.02)
            assert final_state is not None, "job did not reach CANCELLED in time"
            assert final_state["termination_path"] in ("graceful", "killed")
        finally:
            await client.close()

    asyncio.run(_run())
