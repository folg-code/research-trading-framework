"""Job submit/get/list/log endpoint bodies (Sprint 064 T006).

Transport-independent by design, same pattern as `datasets_endpoint.py`:
builds plain JSON-serializable payloads from `JobRecord`; `app.py` is the
only file that imports `aiohttp`.
"""

from __future__ import annotations

from typing import Any

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.job_runner import JobRunner, JobSubmissionError, SubmitSignalResearchJobRequest
from workbench_core.job_store import JobNotFoundError, JobRecord


class JobRequestError(ValueError):
    """Raised for a malformed job submission request body."""


def build_submit_signal_research_job_response(
    runner: JobRunner, body: dict[str, Any]
) -> dict[str, Any]:
    definition_path = body.get("definition_path")
    if not isinstance(definition_path, str):
        raise JobRequestError("'definition_path' must be a string")
    try:
        record = runner.submit_signal_research_job(
            SubmitSignalResearchJobRequest(definition_path=definition_path)
        )
    except JobSubmissionError as exc:
        raise JobRequestError(str(exc)) from exc
    return _job_to_json(record)


def build_get_job_response(runner: JobRunner, job_id: str) -> dict[str, Any]:
    try:
        record = runner.get_job(job_id)
    except JobNotFoundError as exc:
        raise JobRequestError(str(exc)) from exc
    return _job_to_json(record)


def build_list_jobs_response(runner: JobRunner) -> dict[str, Any]:
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "jobs": [_job_to_json(record) for record in runner.list_jobs()],
    }


def _job_to_json(record: JobRecord) -> dict[str, Any]:
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "job_id": record.job_id,
        "job_kind": record.job_kind,
        "state": record.state.value,
        # exposed deliberately, unlike a research dataset's storage path
        # (ADR-0037 section 4): ADR-0041 section 3 requires an operator can
        # rerun the exact same study by hand from this file.
        "config_path": record.config_path,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "started_at": record.started_at.isoformat() if record.started_at else None,
        "finished_at": record.finished_at.isoformat() if record.finished_at else None,
        "exit_code": record.exit_code,
        "latest_phase": record.latest_phase,
    }
