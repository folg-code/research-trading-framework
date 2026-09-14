"""Job runner core: FIFO queue, subprocess spawn, phase parsing (Sprint 064 T006).

ADR-0041 section 2: **one job = one OS subprocess invoking `trading-cli`.**
This module never calls `run_signal_research` (or any other research
workflow) in-process -- the subprocess is the only execution path, so a
crash, an OOM or a segfault in a heavy Polars operation kills the job, not
the control API, and cancellation (T007) is a signal to a process rather
than a cooperative flag threaded through call sites.

D-S064-03's default concurrency (one job at a time, FIFO) is enforced by an
`asyncio.Semaphore` guarding a single background worker task that drains an
`asyncio.Queue` -- not a thread pool or an external broker (ADR-0041 section
8: no Celery/Redis/RQ, that reconsideration trigger has not fired).

Cancellation and restart reconciliation are explicitly T007 -- this module
only reaches `SUCCEEDED`/`FAILED` (ADR-0041 section 4, the two terminal
states this sprint implements).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from workbench_core.job_store import (
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

#: Sprint 064 implements exactly one job kind end to end (T008 is Signal
#: Research only); a new job kind is a deliberate addition here, not a
#: silent widening.
_SUPPORTED_JOB_KINDS = ("research.run.signal",)

_DEFAULT_CLI_COMMAND: tuple[str, ...] = ("uv", "run", "trading-cli")


class JobSubmissionError(ValueError):
    """Raised when a job submission request is invalid."""


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
        cli_command: Sequence[str] = _DEFAULT_CLI_COMMAND,
    ) -> None:
        self._jobs_root = jobs_root
        self._storage_root = storage_root
        self._cli_command = tuple(cli_command)
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._worker_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the background worker draining the FIFO queue."""
        self._jobs_root.mkdir(parents=True, exist_ok=True)
        self._worker_task = asyncio.ensure_future(self._worker_loop())

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

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            async with self._semaphore:
                await self._run_job(job_id)

    async def _run_job(self, job_id: str) -> None:
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
            cwd=str(_repo_root()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        record.pid = process.pid
        write_job_record(self._jobs_root, record)

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
        record.exit_code = exit_code
        record.finished_at = datetime.now(tz=UTC)
        record.updated_at = record.finished_at
        record.state = JobState.SUCCEEDED if exit_code == 0 else JobState.FAILED
        write_job_record(self._jobs_root, record)


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
    return yaml.safe_dump(config, sort_keys=False)


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


def _repo_root() -> Path:
    # apps/workbench/src/workbench_core/job_runner.py -> repo root
    return Path(__file__).resolve().parents[4]
