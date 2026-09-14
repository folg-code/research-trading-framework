"""Tests for the job.json lifecycle state store (Sprint 064 T006, ADR-0041 section 3)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from workbench_core.job_store import (
    JobNotFoundError,
    JobRecord,
    JobState,
    job_json_path,
    list_job_records,
    new_job_id,
    read_job_record,
    write_job_record,
)

_NOW = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)


def _record(job_id: str, *, created_at: datetime = _NOW) -> JobRecord:
    return JobRecord(
        job_id=job_id,
        job_kind="research.run.signal",
        state=JobState.QUEUED,
        config_path=f"/jobs/{job_id}/config.yaml",
        created_at=created_at,
        updated_at=created_at,
    )


def test_job_record_round_trips_through_dict() -> None:
    record = _record("job-1")
    record.state = JobState.RUNNING
    record.pid = 1234
    record.latest_phase = {"name": "evaluate", "index": 4, "of": 5}

    restored = JobRecord.from_dict(record.to_dict())

    assert restored == record


def test_write_then_read_job_record(tmp_path: Path) -> None:
    record = _record("job-1")

    write_job_record(tmp_path, record)

    assert job_json_path(tmp_path, "job-1").is_file()
    assert read_job_record(tmp_path, "job-1") == record


def test_read_job_record_missing_raises_job_not_found(tmp_path: Path) -> None:
    with pytest.raises(JobNotFoundError):
        read_job_record(tmp_path, "does-not-exist")


def test_list_job_records_orders_oldest_first(tmp_path: Path) -> None:
    older = _record("job-older", created_at=datetime(2026, 9, 14, 10, 0, tzinfo=UTC))
    newer = _record("job-newer", created_at=datetime(2026, 9, 14, 11, 0, tzinfo=UTC))
    write_job_record(tmp_path, newer)
    write_job_record(tmp_path, older)

    records = list_job_records(tmp_path)

    assert [record.job_id for record in records] == ["job-older", "job-newer"]


def test_list_job_records_empty_root_returns_empty_list(tmp_path: Path) -> None:
    assert list_job_records(tmp_path / "does-not-exist") == []


def test_new_job_id_returns_distinct_values() -> None:
    assert new_job_id() != new_job_id()
