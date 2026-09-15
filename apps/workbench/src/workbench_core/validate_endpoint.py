"""Preflight-validate endpoint body (Sprint 064 T008).

Transport-independent by design, same pattern as `datasets_endpoint.py`.
"""

from __future__ import annotations

from typing import Any

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.config import WorkbenchApiConfig
from workbench_core.validate_definition import (
    ValidateSignalResearchDefinitionRequest,
    validate_signal_research_definition,
)


class ValidateRequestError(ValueError):
    """Raised for a malformed validate request body."""


async def build_validate_response(
    config: WorkbenchApiConfig, body: dict[str, Any]
) -> dict[str, Any]:
    definition = body.get("definition")
    if not isinstance(definition, dict):
        raise ValidateRequestError("'definition' must be a JSON object")
    outcome = await validate_signal_research_definition(
        ValidateSignalResearchDefinitionRequest(definition=definition),
        storage_root=config.storage_root,
    )
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "ok": outcome.ok,
        "plan": outcome.plan,
        "error_type": outcome.error_type,
        "error_message": outcome.error_message,
    }
