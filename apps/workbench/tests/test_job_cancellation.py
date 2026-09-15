"""Tests for job cancellation and restart reconciliation (Sprint 064 T007,
ADR-0041 sections 5-6, D-S064-03).

Windows-only -- the maintainer's platform is Windows and this file exercises
real Win32 process-tree behaviour (`windows_process.py`); CI runs on
`ubuntu-latest`, so the whole module is skipped there rather than faked.
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
from pathlib import Path

import pytest

from workbench_core.job_runner import (
    JobCancellationError,
    JobRunner,
    SubmitSignalResearchJobRequest,
    read_job_log,
)
from workbench_core.job_store import JobState, write_job_record
from workbench_core.windows_process import IS_WINDOWS, process_creation_time

pytestmark = pytest.mark.skipif(
    not IS_WINDOWS, reason="process-tree cancellation is Windows-only this sprint (ADR-0041 §6)"
)

_LONG_RUNNING_CHILD = textwrap.dedent(
    """
    import time
    print("running", flush=True)
    time.sleep(30)
    """
)

_IGNORES_GRACEFUL_SIGNAL_CHILD = textwrap.dedent(
    """
    import signal
    import time

    def _ignore(signum, frame):
        pass

    signal.signal(signal.SIGBREAK, _ignore)
    print("running", flush=True)
    time.sleep(30)
    """
)

_SUCCEEDING_CHILD = textwrap.dedent(
    """
    import sys
    print("done", flush=True)
    sys.exit(0)
    """
)


def _write_stub(tmp_path: Path, name: str, script: str) -> tuple[str, ...]:
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    return (sys.executable, str(path))


async def _wait_for_state(runner: JobRunner, job_id: str, states: tuple[JobState, ...]) -> None:
    for _attempt in range(500):
        if runner.get_job(job_id).state in states:
            return
        await asyncio.sleep(0.02)
    pytest.fail(f"job {job_id} did not reach {states} in time")


def _process_is_dead(pid: int | None) -> bool:
    return pid is None or process_creation_time(pid) is None


async def _wait_for_log_line(jobs_root: Path, job_id: str, text: str) -> None:
    """Poll `stdout.log` for `text` -- used to confirm a stub child has
    actually finished its own startup (e.g. registered a signal handler)
    before the test sends it a signal; `JobState.RUNNING` only means the OS
    process object exists, not that the child has run any of its own code
    yet, so cancelling immediately on RUNNING races the child's own
    Python/interpreter startup."""
    for _attempt in range(500):
        if text in read_job_log(jobs_root, job_id):
            return
        await asyncio.sleep(0.02)
    pytest.fail(f"job {job_id!r}'s log never contained {text!r} in time")


def test_cancel_running_job_terminates_gracefully(tmp_path: Path) -> None:
    """The default (no signal handler installed) child dies immediately on
    CTRL_BREAK -- well within the grace window, so the graceful path is
    taken, never escalating to a hard kill."""
    cli_command = _write_stub(tmp_path, "child.py", _LONG_RUNNING_CHILD)
    # A generous grace window that is still comfortably smaller than
    # `_wait_for_state`'s own ~10s polling budget below -- equal (or larger)
    # budgets on both sides race each other on any timing hiccup, which is
    # exactly what made this test flake once (job never observed reaching a
    # terminal state in time even though the mechanism itself was fine).
    runner = JobRunner(
        jobs_root=tmp_path / "jobs",
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
        graceful_termination_seconds=3.0,
    )
    jobs_root = tmp_path / "jobs"

    async def _scenario() -> str:
        runner.start()
        try:
            record = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="a.yaml")
            )
            await _wait_for_state(runner, record.job_id, (JobState.RUNNING,))
            # As in the hard-kill test below: `JobState.RUNNING` only means
            # the OS process object exists, not that the new process group
            # is fully set up to receive a console control event yet -- a
            # CTRL_BREAK sent too early can be silently dropped. Waiting for
            # the child's own first print is a real readiness signal.
            await _wait_for_log_line(jobs_root, record.job_id, "running")
            runner.cancel_job(record.job_id)
            await _wait_for_state(
                runner, record.job_id, (JobState.CANCELLED, JobState.FAILED, JobState.SUCCEEDED)
            )
        finally:
            await runner.stop()
        return record.job_id

    job_id = asyncio.run(_scenario())

    final = runner.get_job(job_id)
    assert final.state is JobState.CANCELLED
    assert final.termination_path == "graceful"
    assert final.cancel_requested is True
    assert _process_is_dead(final.pid)


def test_cancel_running_job_escalates_to_hard_kill_after_grace(tmp_path: Path) -> None:
    """A child that ignores CTRL_BREAK must still die -- via the Job Object
    tree-kill -- once the (short, test-only) grace window elapses."""
    cli_command = _write_stub(tmp_path, "child.py", _IGNORES_GRACEFUL_SIGNAL_CHILD)
    runner = JobRunner(
        jobs_root=tmp_path / "jobs",
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
        graceful_termination_seconds=0.5,
    )

    jobs_root = tmp_path / "jobs"

    async def _scenario() -> str:
        runner.start()
        try:
            record = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="a.yaml")
            )
            await _wait_for_state(runner, record.job_id, (JobState.RUNNING,))
            # Confirm the child has actually installed its ignore-CTRL_BREAK
            # handler before cancelling -- otherwise this races the child's
            # own interpreter startup and the OS default handler (immediate
            # exit) can fire instead, which would make this test pass for
            # the wrong reason (or flake).
            await _wait_for_log_line(jobs_root, record.job_id, "running")
            runner.cancel_job(record.job_id)
            await _wait_for_state(
                runner, record.job_id, (JobState.CANCELLED, JobState.FAILED, JobState.SUCCEEDED)
            )
        finally:
            await runner.stop()
        return record.job_id

    job_id = asyncio.run(_scenario())

    final = runner.get_job(job_id)
    assert final.state is JobState.CANCELLED
    assert final.termination_path == "killed"


def test_cancel_queued_job_is_immediate_with_no_subprocess(tmp_path: Path) -> None:
    """D-S064-03's QUEUEING rule: cancelling a QUEUED job is immediate,
    terminal, and spawns nothing -- proven here by a concurrency-1 runner
    whose first job blocks the queue for the whole test."""
    cli_command = _write_stub(tmp_path, "child.py", _LONG_RUNNING_CHILD)
    jobs_root = tmp_path / "jobs"
    runner = JobRunner(
        jobs_root=jobs_root,
        storage_root=tmp_path / "workspace",
        cli_command=cli_command,
        max_concurrent_jobs=1,
        graceful_termination_seconds=3.0,
    )

    async def _scenario() -> tuple[str, str]:
        runner.start()
        try:
            blocking = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="blocking.yaml")
            )
            await _wait_for_state(runner, blocking.job_id, (JobState.RUNNING,))
            # Readiness, not just RUNNING -- see the graceful-termination
            # test above for why an immediate CTRL_BREAK can be dropped.
            await _wait_for_log_line(jobs_root, blocking.job_id, "running")
            queued = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="queued.yaml")
            )
            assert runner.get_job(queued.job_id).state is JobState.QUEUED

            cancelled = runner.cancel_job(queued.job_id)
            assert cancelled.state is JobState.QUEUED  # cancel_requested set, not yet drained

            runner.cancel_job(blocking.job_id)
            await _wait_for_state(
                runner,
                blocking.job_id,
                (JobState.CANCELLED, JobState.FAILED, JobState.SUCCEEDED),
            )
            await _wait_for_state(runner, queued.job_id, (JobState.CANCELLED,))
        finally:
            await runner.stop()
        return blocking.job_id, queued.job_id

    _blocking_id, queued_id = asyncio.run(_scenario())

    final = runner.get_job(queued_id)
    assert final.state is JobState.CANCELLED
    assert final.pid is None  # never spawned
    assert final.termination_path is None


def test_cancel_already_terminal_job_raises(tmp_path: Path) -> None:
    cli_command = _write_stub(tmp_path, "child.py", _SUCCEEDING_CHILD)
    runner = JobRunner(
        jobs_root=tmp_path / "jobs", storage_root=tmp_path / "workspace", cli_command=cli_command
    )

    async def _scenario() -> str:
        runner.start()
        try:
            record = runner.submit_signal_research_job(
                SubmitSignalResearchJobRequest(definition_path="a.yaml")
            )
            await _wait_for_state(runner, record.job_id, (JobState.SUCCEEDED,))
        finally:
            await runner.stop()
        return record.job_id

    job_id = asyncio.run(_scenario())

    with pytest.raises(JobCancellationError):
        runner.cancel_job(job_id)


def test_reconcile_marks_dead_pid_interrupted(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from workbench_core.job_store import JobRecord

    jobs_root = tmp_path / "jobs"
    now = datetime.now(tz=UTC)
    write_job_record(
        jobs_root,
        JobRecord(
            job_id="dead-pid-job",
            job_kind="research.run.signal",
            state=JobState.RUNNING,
            config_path=str(tmp_path / "config.yaml"),
            created_at=now,
            updated_at=now,
            started_at=now,
            pid=999_999_999,  # not a real pid
            process_start_time=123,
        ),
    )
    runner = JobRunner(jobs_root=jobs_root, storage_root=tmp_path / "workspace")

    runner.reconcile_jobs_on_startup()

    final = runner.get_job("dead-pid-job")
    assert final.state is JobState.INTERRUPTED
    assert final.interrupted_reason


def test_reconcile_marks_recycled_pid_interrupted(tmp_path: Path) -> None:
    """A live pid whose creation time does not match the recorded one is
    treated as a *different* process -- the OS recycled the pid."""
    import os
    from datetime import UTC, datetime

    from workbench_core.job_store import JobRecord

    jobs_root = tmp_path / "jobs"
    now = datetime.now(tz=UTC)
    real_pid = os.getpid()  # alive, but its real creation time won't match
    write_job_record(
        jobs_root,
        JobRecord(
            job_id="recycled-pid-job",
            job_kind="research.run.signal",
            state=JobState.RUNNING,
            config_path=str(tmp_path / "config.yaml"),
            created_at=now,
            updated_at=now,
            started_at=now,
            pid=real_pid,
            process_start_time=-1,  # deliberately wrong
        ),
    )
    runner = JobRunner(jobs_root=jobs_root, storage_root=tmp_path / "workspace")

    runner.reconcile_jobs_on_startup()

    final = runner.get_job("recycled-pid-job")
    assert final.state is JobState.INTERRUPTED


def test_reconcile_leaves_matching_pid_running(tmp_path: Path) -> None:
    import os
    from datetime import UTC, datetime

    from workbench_core.job_store import JobRecord

    jobs_root = tmp_path / "jobs"
    now = datetime.now(tz=UTC)
    real_pid = os.getpid()
    real_creation_time = process_creation_time(real_pid)
    assert real_creation_time is not None
    write_job_record(
        jobs_root,
        JobRecord(
            job_id="still-running-job",
            job_kind="research.run.signal",
            state=JobState.RUNNING,
            config_path=str(tmp_path / "config.yaml"),
            created_at=now,
            updated_at=now,
            started_at=now,
            pid=real_pid,
            process_start_time=real_creation_time,
        ),
    )
    runner = JobRunner(jobs_root=jobs_root, storage_root=tmp_path / "workspace")

    runner.reconcile_jobs_on_startup()

    final = runner.get_job("still-running-job")
    assert final.state is JobState.RUNNING
