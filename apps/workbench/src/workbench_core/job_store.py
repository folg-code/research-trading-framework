"""Job lifecycle state store (Sprint 064 T006, ADR-0041 section 3).

``user_data/workbench/jobs/<job_id>/`` holds ``job.json`` (this module's own
state), ``config.yaml`` (the exact generated `trading-cli` config -- an
operator can rerun the job by hand from it) and ``stdout.log`` (verbatim
child output). ``job.json`` is **workbench-owned lifecycle state, never
research truth** -- deleting the whole ``jobs/`` tree loses no research
artifact and no persisted research fact; nothing else in the repository
reads it.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

JOB_STATE_SCHEMA_VERSION = "workbench.job_state.v1"


class JobState(StrEnum):
    """ADR-0041 section 4's state machine, now complete (Sprint 064 T007)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


#: ADR-0041 section 4: "Terminal states are terminal." Enforced by
#: `write_job_record` below, not left to callers to remember.
TERMINAL_JOB_STATES = frozenset(
    {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, JobState.INTERRUPTED}
)


class JobNotFoundError(LookupError):
    """Raised when a `job_id` has no `job.json` under the jobs root."""


class JobStateTransitionError(ValueError):
    """Raised by `write_job_record` when a write would move a job's state
    away from an already-terminal one (ADR-0041 section 4)."""


@dataclass(slots=True)
class JobRecord:
    """One job's lifecycle state -- the exact content of its `job.json`."""

    job_id: str
    job_kind: str
    state: JobState
    config_path: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pid: int | None = None
    process_start_time: int | None = None
    exit_code: int | None = None
    latest_phase: dict[str, Any] | None = None
    cancel_requested: bool = False
    termination_path: str | None = None
    interrupted_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": JOB_STATE_SCHEMA_VERSION,
            "job_id": self.job_id,
            "job_kind": self.job_kind,
            "state": self.state.value,
            "config_path": self.config_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "pid": self.pid,
            "process_start_time": self.process_start_time,
            "exit_code": self.exit_code,
            "latest_phase": self.latest_phase,
            "cancel_requested": self.cancel_requested,
            "termination_path": self.termination_path,
            "interrupted_reason": self.interrupted_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JobRecord:
        return cls(
            job_id=data["job_id"],
            job_kind=data["job_kind"],
            state=JobState(data["state"]),
            config_path=data["config_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=_parse_optional_datetime(data.get("started_at")),
            finished_at=_parse_optional_datetime(data.get("finished_at")),
            pid=data.get("pid"),
            process_start_time=data.get("process_start_time"),
            exit_code=data.get("exit_code"),
            latest_phase=data.get("latest_phase"),
            cancel_requested=bool(data.get("cancel_requested", False)),
            termination_path=data.get("termination_path"),
            interrupted_reason=data.get("interrupted_reason"),
        )


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def new_job_id() -> str:
    return uuid.uuid4().hex


def job_dir(jobs_root: Path, job_id: str) -> Path:
    return jobs_root / job_id


def job_json_path(jobs_root: Path, job_id: str) -> Path:
    return job_dir(jobs_root, job_id) / "job.json"


def config_yaml_path(jobs_root: Path, job_id: str) -> Path:
    return job_dir(jobs_root, job_id) / "config.yaml"


def stdout_log_path(jobs_root: Path, job_id: str) -> Path:
    return job_dir(jobs_root, job_id) / "stdout.log"


def write_job_record(jobs_root: Path, record: JobRecord) -> None:
    """Overwrite `job.json` with `record`'s current state, creating the job's
    directory if this is its first write.

    Refuses a write that would move a job OUT of an already-terminal state
    (ADR-0041 section 4: "Terminal states are terminal. No automatic retry,
    no resume, no requeue.") -- a same-state terminal rewrite (e.g. updating
    `updated_at`) is still allowed.
    """
    path = job_json_path(jobs_root, record.job_id)
    if path.is_file():
        existing = JobRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if existing.state in TERMINAL_JOB_STATES and record.state != existing.state:
            msg = (
                f"job {record.job_id!r} is already terminal ({existing.state.value}); "
                f"refusing to write state={record.state.value}"
            )
            raise JobStateTransitionError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def read_job_record(jobs_root: Path, job_id: str) -> JobRecord:
    path = job_json_path(jobs_root, job_id)
    if not path.is_file():
        msg = f"no job found for job_id={job_id!r}"
        raise JobNotFoundError(msg)
    return JobRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_job_records(jobs_root: Path) -> list[JobRecord]:
    """Return every job under `jobs_root`, oldest first. Empty if the root is missing."""
    if not jobs_root.is_dir():
        return []
    records = [
        read_job_record(jobs_root, entry.name)
        for entry in sorted(jobs_root.iterdir())
        if entry.is_dir() and job_json_path(jobs_root, entry.name).is_file()
    ]
    records.sort(key=lambda record: record.created_at)
    return records
