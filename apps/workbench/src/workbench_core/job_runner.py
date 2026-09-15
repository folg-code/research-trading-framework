"""Job runner core: FIFO queue, subprocess spawn, phase parsing, cancellation
and restart reconciliation (Sprint 064 T006/T007).

ADR-0041 section 2: **one job = one OS subprocess invoking `trading-cli`.**
This module never calls `run_signal_research` (or any other research
workflow) in-process -- the subprocess is the only execution path, so a
crash, an OOM or a segfault in a heavy Polars operation kills the job, not
the control API, and cancellation is a signal to a process rather than a
cooperative flag threaded through call sites.

D-S064-03's default concurrency (one job at a time, FIFO) is enforced by an
`asyncio.Semaphore` guarding a single background worker task that drains an
`asyncio.Queue` -- not a thread pool or an external broker (ADR-0041 section
8: no Celery/Redis/RQ, that reconsideration trigger has not fired).

Cancellation (ADR-0041 section 6, D-S064-03's graceful window) and restart
reconciliation (ADR-0041 section 5) are both Windows-only in their real
implementation -- graceful `CTRL_BREAK_EVENT` plus a Job Object tree-kill for
the hard-kill escalation, and a pid/process-creation-time check for
reconciliation (`windows_process.py`; the maintainer's platform is Windows,
CI runs on `ubuntu-latest`). On a non-Windows platform this module falls
back to a plain `terminate()`/`kill()` on the root process only, and restart
reconciliation always treats a QUEUED/RUNNING job as no longer verifiably
alive -- correct in spirit (single-process, not tree-aware) but not the
behaviour this sprint's acceptance criteria were verified against.
"""

from __future__ import annotations

import asyncio
import json
import signal
import subprocess
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from workbench_core.job_store import (
    TERMINAL_JOB_STATES,
    JobRecord,
    JobState,
    config_yaml_path,
    job_dir,
    list_job_records,
    new_job_id,
    read_job_record,
    stdout_log_path,
    write_job_record,
)
from workbench_core.windows_process import (
    IS_WINDOWS,
    assign_process_to_job,
    close_handle,
    create_job_object,
    process_creation_time,
    terminate_job_object,
)

#: Sprint 064 implements exactly one job kind end to end (T008 is Signal
#: Research only); a new job kind is a deliberate addition here, not a
#: silent widening.
_SUPPORTED_JOB_KINDS = ("research.run.signal",)

#: Public (not underscore-prefixed): `app.py`'s `create_app` references this
#: directly to resolve its own optional override parameter to the same
#: default `JobRunner` itself would use.
DEFAULT_CLI_COMMAND: tuple[str, ...] = ("uv", "run", "trading-cli")

#: D-S064-03, approved 2026-09-14 (raised from a 10s starting proposal at the
#: maintainer's request): SIGTERM/CTRL_BREAK, then this long to unwind, then
#: a hard kill. Public for the same reason as `DEFAULT_CLI_COMMAND` above.
DEFAULT_GRACEFUL_TERMINATION_SECONDS = 20.0

_INTERRUPTED_REASON = "the application or worker restarted while this job was active"

_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


class JobSubmissionError(ValueError):
    """Raised when a job submission request is invalid."""


class JobCancellationError(ValueError):
    """Raised when a job cannot be cancelled (already terminal, or not found
    in this runner's in-memory tracking for a RUNNING job -- e.g. it finished
    in the moment between the caller's status read and the cancel call)."""


@dataclass(frozen=True, slots=True)
class SubmitSignalResearchJobRequest:
    """A `research.run.signal` submission: the definition file, nothing else.

    Building the config from a template/override payload is T008's concern
    (the UI slice); this request already assumes a
    `SignalResearchDefinitionSpec` file exists on disk, the same shape
    `trading-cli research run signal` itself consumes (`research.signal.definition`).
    """

    definition_path: str


class JobRunner:
    """Owns the FIFO job queue and the single subprocess execution slot."""

    def __init__(
        self,
        *,
        jobs_root: Path,
        storage_root: Path,
        max_concurrent_jobs: int = 1,
        cli_command: Sequence[str] = DEFAULT_CLI_COMMAND,
        graceful_termination_seconds: float = DEFAULT_GRACEFUL_TERMINATION_SECONDS,
    ) -> None:
        self._jobs_root = jobs_root
        self._storage_root = storage_root
        self._cli_command = tuple(cli_command)
        self._graceful_termination_seconds = graceful_termination_seconds
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._worker_task: asyncio.Task[None] | None = None
        #: RUNNING jobs only, keyed by job_id -- populated/removed by
        #: `_run_job` itself. Never persisted: after a restart there is
        #: nothing here to cancel against, by design (see `reconcile_jobs_on_startup`).
        self._cancel_events: dict[str, asyncio.Event] = {}

    def start(self) -> None:
        """Start the background worker draining the FIFO queue.

        Runs restart reconciliation first (ADR-0041 section 5) -- the
        in-memory queue is always empty on a fresh `JobRunner`, so any
        QUEUED/RUNNING job left over from a previous incarnation would
        otherwise never be revisited at all.
        """
        self._jobs_root.mkdir(parents=True, exist_ok=True)
        self.reconcile_jobs_on_startup()
        self._worker_task = asyncio.ensure_future(self._worker_loop())

    def reconcile_jobs_on_startup(self) -> None:
        """ADR-0041 section 5: a QUEUED/RUNNING job survives reconciliation
        only if its recorded pid is alive AND its process creation time still
        matches what was recorded when it started (rules out a recycled
        pid) -- otherwise it becomes INTERRUPTED, a distinct terminal state,
        never displayed as failed/cancelled/running. Windows-only in its real
        form; see the module docstring for the non-Windows fallback."""
        for record in list_job_records(self._jobs_root):
            if record.state not in (JobState.QUEUED, JobState.RUNNING):
                continue
            if self._is_still_alive(record):
                continue
            record.state = JobState.INTERRUPTED
            record.interrupted_reason = _INTERRUPTED_REASON
            record.finished_at = datetime.now(tz=UTC)
            record.updated_at = record.finished_at
            write_job_record(self._jobs_root, record)

    def _is_still_alive(self, record: JobRecord) -> bool:
        if not IS_WINDOWS or record.pid is None or record.process_start_time is None:
            return False
        return process_creation_time(record.pid) == record.process_start_time

    async def stop(self) -> None:
        """Stop the worker. A job already spawned keeps running (ADR-0041 section 2:
        the subprocess, not this task, owns its own lifetime) -- this only
        stops picking up new queued jobs."""
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await self._worker_task
        self._worker_task = None

    def submit_signal_research_job(self, request: SubmitSignalResearchJobRequest) -> JobRecord:
        """Write `config.yaml` + `job.json` and enqueue the job. Does not run it."""
        job_kind = "research.run.signal"
        if job_kind not in _SUPPORTED_JOB_KINDS:  # pragma: no cover - defensive, always true today
            raise JobSubmissionError(f"unsupported job_kind: {job_kind!r}")
        if not request.definition_path.strip():
            raise JobSubmissionError("definition_path must be non-empty")

        job_id = new_job_id()
        job_dir(self._jobs_root, job_id).mkdir(parents=True, exist_ok=False)
        config_path = config_yaml_path(self._jobs_root, job_id)
        config_path.write_text(
            _render_signal_research_config_yaml(
                storage_root=self._storage_root, definition_path=request.definition_path
            ),
            encoding="utf-8",
        )

        now = datetime.now(tz=UTC)
        record = JobRecord(
            job_id=job_id,
            job_kind=job_kind,
            state=JobState.QUEUED,
            config_path=str(config_path),
            created_at=now,
            updated_at=now,
        )
        write_job_record(self._jobs_root, record)
        self._queue.put_nowait(job_id)
        return record

    def get_job(self, job_id: str) -> JobRecord:
        return read_job_record(self._jobs_root, job_id)

    def list_jobs(self) -> list[JobRecord]:
        return list_job_records(self._jobs_root)

    def cancel_job(self, job_id: str) -> JobRecord:
        """Request cancellation of a QUEUED or RUNNING job (ADR-0041 section 6).

        QUEUED: marked immediately, terminal, with no subprocess ever spawned
        (D-S064-03's QUEUEING rule). RUNNING: signals the in-flight `_run_job`
        task to begin graceful-then-hard termination; this call returns as
        soon as that signal is set, not once the job actually reaches
        CANCELLED -- poll `get_job` for the terminal state.
        """
        record = read_job_record(self._jobs_root, job_id)
        if record.state in TERMINAL_JOB_STATES:
            msg = f"job {job_id!r} is already {record.state.value}; cannot cancel"
            raise JobCancellationError(msg)
        if record.state is JobState.QUEUED:
            record.cancel_requested = True
            record.updated_at = datetime.now(tz=UTC)
            write_job_record(self._jobs_root, record)
            return record
        cancel_event = self._cancel_events.get(job_id)
        if cancel_event is None:
            msg = f"job {job_id!r} is not currently tracked as running; cannot cancel"
            raise JobCancellationError(msg)
        cancel_event.set()
        return record

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            async with self._semaphore:
                record = read_job_record(self._jobs_root, job_id)
                if record.cancel_requested:
                    # Cancelled while still QUEUED: terminal, no subprocess spawned.
                    record.state = JobState.CANCELLED
                    record.finished_at = datetime.now(tz=UTC)
                    record.updated_at = record.finished_at
                    write_job_record(self._jobs_root, record)
                    continue
                await self._run_job(job_id)

    async def _run_job(self, job_id: str) -> None:
        # Registered before the state is even written RUNNING: `cancel_job`
        # only checks `self._cancel_events` for a RUNNING job, so the event
        # must exist no later than the state does, not after the (slower)
        # subprocess spawn below -- otherwise a cancel racing right behind a
        # status poll that just observed RUNNING could find no event to set.
        cancel_event = asyncio.Event()
        self._cancel_events[job_id] = cancel_event

        record = read_job_record(self._jobs_root, job_id)
        record.state = JobState.RUNNING
        record.started_at = datetime.now(tz=UTC)
        record.updated_at = record.started_at
        write_job_record(self._jobs_root, record)

        process = await asyncio.create_subprocess_exec(
            *self._cli_command,
            "research",
            "run",
            "--config",
            record.config_path,
            "--json",
            cwd=str(repo_root()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=_CREATE_NEW_PROCESS_GROUP,
        )
        record.pid = process.pid
        record.process_start_time = process_creation_time(process.pid) if IS_WINDOWS else None
        write_job_record(self._jobs_root, record)

        job_handle = None
        if IS_WINDOWS:
            job_handle = create_job_object()
            assign_process_to_job(job_handle, process.pid)

        cancel_task = asyncio.ensure_future(
            self._cancel_watcher(job_id, cancel_event, process, job_handle)
        )
        try:
            log_path = stdout_log_path(self._jobs_root, job_id)
            assert process.stdout is not None
            with log_path.open("w", encoding="utf-8") as log_file:
                async for raw_line in process.stdout:
                    line = raw_line.decode("utf-8", errors="replace")
                    log_file.write(line)
                    log_file.flush()
                    phase = _parse_phase_event(line)
                    if phase is not None:
                        record.latest_phase = phase
                        record.updated_at = datetime.now(tz=UTC)
                        write_job_record(self._jobs_root, record)

            exit_code = await process.wait()
        finally:
            if cancel_event.is_set():
                # A cancellation was requested: `_cancel_watcher` is either
                # already done or about to finish naturally (the process it
                # is watching just exited too) -- let it, so its real
                # "graceful"/"killed" result is preserved instead of racing
                # `.cancel()` against its own last `await`.
                with suppress(asyncio.CancelledError):
                    await cancel_task
            else:
                # Never cancelled: `_cancel_watcher` is parked at
                # `cancel_event.wait()` forever otherwise.
                cancel_task.cancel()
                with suppress(asyncio.CancelledError):
                    await cancel_task
            del self._cancel_events[job_id]
            if job_handle is not None:
                close_handle(job_handle)

        # A single final write, incorporating whatever `_cancel_watcher`
        # observed -- avoids two coroutines racing to write the terminal
        # record. `record.cancel_requested` (re-read here) is the ground
        # truth for whether this was a cancellation, in case `cancel_task`
        # was still cut off by the shutdown-ordering edge case above.
        termination_path = cancel_task.result() if not cancel_task.cancelled() else None
        record = read_job_record(self._jobs_root, job_id)
        record.exit_code = exit_code
        record.finished_at = datetime.now(tz=UTC)
        record.updated_at = record.finished_at
        record.termination_path = termination_path
        record.state = (
            JobState.CANCELLED
            if record.cancel_requested
            else (JobState.SUCCEEDED if exit_code == 0 else JobState.FAILED)
        )
        write_job_record(self._jobs_root, record)

    async def _cancel_watcher(
        self,
        job_id: str,
        cancel_event: asyncio.Event,
        process: asyncio.subprocess.Process,
        job_handle: int | None,
    ) -> str:
        """Wait for `cancel_job` to signal this job, then run the
        graceful-then-hard termination sequence (ADR-0041 section 6,
        D-S064-03's window), and return which path was taken ("graceful" or
        "killed") -- `_run_job` uses the return value to decide the job's
        final state, so there is only ever one writer of the terminal
        record. `_run_job` cancels this task once the process exits on its
        own, without this coroutine ever getting past `cancel_event.wait()`.
        """
        await cancel_event.wait()
        record = read_job_record(self._jobs_root, job_id)
        record.cancel_requested = True
        record.updated_at = datetime.now(tz=UTC)
        write_job_record(self._jobs_root, record)

        if IS_WINDOWS:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:  # pragma: no cover - non-Windows fallback, not this sprint's target platform
            process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=self._graceful_termination_seconds)
            return "graceful"
        except TimeoutError:
            if IS_WINDOWS and job_handle is not None:
                terminate_job_object(job_handle)
            else:  # pragma: no cover - non-Windows fallback
                process.kill()
            return "killed"


def read_job_log(jobs_root: Path, job_id: str) -> str:
    """Return the verbatim `stdout.log` written so far for `job_id`."""
    path = stdout_log_path(jobs_root, job_id)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _render_signal_research_config_yaml(*, storage_root: Path, definition_path: str) -> str:
    """The exact `trading-cli research run signal` config (D-S064's own
    schema, T002) -- byte-for-byte usable by an operator running `trading-cli`
    directly (ADR-0041 section 3's acceptance)."""
    config: dict[str, Any] = {
        "version": 1,
        "storage_root": str(storage_root.resolve()),
        "research": {"kind": "signal", "signal": {"definition": definition_path}},
    }
    return str(yaml.safe_dump(config, sort_keys=False))


def _parse_phase_event(line: str) -> dict[str, Any] | None:
    """Parse one `workbench.phase_event.v1` line (D-S064-04); anything else on
    stdout -- including the CLI's own final `--json` summary -- is left as an
    ordinary logged line, not derived from."""
    stripped = line.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("event") != "phase":
        return None
    return payload


def repo_root() -> Path:
    """The repo root `trading-cli` must be spawned from -- shared with
    `validate_definition.py`'s synchronous `--dry-run` invocation."""
    # apps/workbench/src/workbench_core/job_runner.py -> repo root
    return Path(__file__).resolve().parents[4]
