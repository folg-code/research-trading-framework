"""HTTP contract tests for the job submit/get/list/log endpoints (Sprint 064 T006).

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

from aiohttp.test_utils import TestClient, TestServer

from workbench_core.app import create_app
from workbench_core.config import WorkbenchApiConfig
from workbench_core.job_store import JobState

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


def _write_stub(tmp_path: Path) -> tuple[str, ...]:
    path = tmp_path / "succeeding_child.py"
    path.write_text(_SUCCEEDING_CHILD, encoding="utf-8")
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
