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
    """ADR-0041 section 4's state machine. CANCELLED/INTERRUPTED are T007's."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class JobNotFoundError(LookupError):
    """Raised when a `job_id` has no `job.json` under the jobs root."""


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
    exit_code: int | None = None
    latest_phase: dict[str, Any] | None = None

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
            "exit_code": self.exit_code,
            "latest_phase": self.latest_phase,
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
            exit_code=data.get("exit_code"),
            latest_phase=data.get("latest_phase"),
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
    directory if this is its first write."""
    path = job_json_path(jobs_root, record.job_id)
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
