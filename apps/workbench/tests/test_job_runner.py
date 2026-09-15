"""Tests for the job runner core (Sprint 064 T006, ADR-0041 sections 2-4, 8).

A real `trading-cli`/`uv` subprocess is never spawned here (Tier 1,
network-free, no ML extra) -- `JobRunner`'s `cli_command` seam is pointed at
a small stub Python script instead, playing the two shapes a real
`trading-cli research run signal --json` run can take: phase events then a
clean exit, or phase events then a non-zero exit partway through.
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from workbench_core.job_runner import (
    JobRunner,
    JobSubmissionError,
    SubmitSignalResearchJobRequest,
    read_job_log,
)
from workbench_core.job_store import JobRecord, JobState

_SUCCEEDING_CHILD = textwrap.dedent(
    """
    import json
    import sys

    phases = ["load-definition", "resolve-models", "load-dataset", "evaluate", "persist"]
    for index, name in enumerate(phases, start=1):
        print(json.dumps({"event": "phase", "name": name, "index": index, "of": len(phases)}))
    print("ordinary human-readable log line")
    print(json.dumps({"status": "success", "result": {"run_id": "synthetic-run"}}))
    sys.exit(0)
    """
)

_FAILING_CHILD = textwrap.dedent(
    """
    import json
    import sys

    for index, name in enumerate(["load-definition", "resolve-models"], start=1):
        print(json.dumps({"event": "phase", "name": name, "index": index, "of": 5}))
    print("about to fail", file=sys.stdout)
    sys.exit(1)
    """
)


def _write_stub(tmp_path: Path, name: str, script: str) -> tuple[str, ...]:
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    return (sys.executable, str(path))


async def _run_one_job(runner: JobRunner, job_id: str) -> None:
    """Drain exactly one job synchronously, without the background worker
    loop -- keeps each test deterministic without sleeping/polling."""
    await runner._run_job(job_id)


def test_submit_writes_byte_for_byte_usable_config(tmp_path: Path) -> None:
    jobs_root = tmp_path / "jobs"
    storage_root = tmp_path / "workspace"
    runner = JobRunner(jobs_root=jobs_root, storage_root=storage_root)

    record = runner.submit_signal_research_job(
        SubmitSignalResearchJobRequest(definition_path="signal_definition.yaml")
    )

    config = yaml.safe_load(Path(record.config_path).read_text(encoding="utf-8"))
    assert config == {
        "version": 1,
        "storage_root": str(storage_root.resolve()),
        "research": {"kind": "signal", "signal": {"definition": "signal_definition.yaml"}},
    }
    assert record.state is JobState.QUEUED


def test_submit_rejects_blank_definition_path(tmp_path: Path) -> None:
    runner = JobRunner(jobs_root=tmp_path / "jobs", storage_root=tmp_path / "workspace")

    with pytest.raises(JobSubmissionError):
        runner.submit_signal_research_job(SubmitSignalResearchJobRequest(definition_path="  "))


def test_run_job_succeeds_and_records_phases_and_log(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path, "succeeding_child.py", _SUCCEEDING_CHILD)
    runner = JobRunner(
        jobs_root=tmp_path / "jobs",
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
    )
    record = runner.submit_signal_research_job(
        SubmitSignalResearchJobRequest(definition_path="signal_definition.yaml")
    )

    asyncio.run(_run_one_job(runner, record.job_id))

    final = runner.get_job(record.job_id)
    assert final.state is JobState.SUCCEEDED
    assert final.exit_code == 0
    assert final.pid is not None
    assert final.started_at is not None
    assert final.finished_at is not None
    assert final.latest_phase == {"event": "phase", "name": "persist", "index": 5, "of": 5}
    assert final.result == {"run_id": "synthetic-run"}

    log = read_job_log(tmp_path / "jobs", record.job_id)
    assert '"name": "load-definition"' in log
    assert "ordinary human-readable log line" in log
    assert '"run_id": "synthetic-run"' in log


def test_run_job_failure_yields_failed_with_exit_code(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path, "failing_child.py", _FAILING_CHILD)
    runner = JobRunner(
        jobs_root=tmp_path / "jobs",
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
    )
    record = runner.submit_signal_research_job(
        SubmitSignalResearchJobRequest(definition_path="signal_definition.yaml")
    )

    asyncio.run(_run_one_job(runner, record.job_id))

    final = runner.get_job(record.job_id)
    assert final.state is JobState.FAILED
    assert final.exit_code == 1
    # only the two phases the stub actually emitted before failing
    assert final.latest_phase == {"event": "phase", "name": "resolve-models", "index": 2, "of": 5}


def test_fifo_ordering_at_concurrency_one(tmp_path: Path) -> None:
    """D-S064-03: submissions run one at a time, in submission order."""
    cli_command = _write_stub(tmp_path, "succeeding_child.py", _SUCCEEDING_CHILD)
    runner = JobRunner(
        jobs_root=tmp_path / "jobs",
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
        max_concurrent_jobs=1,
    )

    async def _wait_terminal(job_id: str) -> None:
        for _attempt in range(200):
            if runner.get_job(job_id).state in (JobState.SUCCEEDED, JobState.FAILED):
                return
            await asyncio.sleep(0.02)
        pytest.fail(f"job {job_id} did not reach a terminal state in time")

    async def _drive_worker_for_two_jobs() -> tuple[JobRecord, JobRecord]:
        # `start()` first, matching real usage (app.py starts the runner
        # before accepting any submission) -- restart reconciliation only
        # applies to jobs left over from a PRIOR incarnation, not ones
        # submitted after this one is already running.
        runner.start()
        try:
            first = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="a.yaml")
            )
            second = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="b.yaml")
            )
            await _wait_terminal(first.job_id)
            await _wait_terminal(second.job_id)
            return first, second
        finally:
            await runner.stop()

    first, second = asyncio.run(_drive_worker_for_two_jobs())

    first_final = runner.get_job(first.job_id)
    second_final = runner.get_job(second.job_id)
    assert first_final.state is JobState.SUCCEEDED
    assert second_final.state is JobState.SUCCEEDED
    assert first_final.started_at is not None
    assert second_final.started_at is not None
    assert first_final.finished_at is not None
    # the second job never starts before the first one finishes
    assert second_final.started_at >= first_final.finished_at
