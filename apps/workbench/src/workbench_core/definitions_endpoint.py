"""Saved-definition list/save/load endpoint bodies (Sprint 064 T008).

Transport-independent by design, same pattern as `datasets_endpoint.py`.
"""

from __future__ import annotations

from typing import Any

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.config import WorkbenchApiConfig
from workbench_core.definitions_store import (
    DefinitionNotFoundError,
    InvalidDefinitionNameError,
    list_definition_names,
    load_definition,
    save_definition,
)


class DefinitionRequestError(ValueError):
    """Raised for a malformed save/load request, or an invalid/missing name."""


def build_list_definitions_response(config: WorkbenchApiConfig) -> dict[str, Any]:
    names = list_definition_names(config.storage_root)
    return {"schema_version": WORKBENCH_API_VERSION, "definitions": list(names)}


def build_save_definition_response(
    config: WorkbenchApiConfig, body: dict[str, Any]
) -> dict[str, Any]:
    name = body.get("name")
    definition = body.get("definition")
    if not isinstance(name, str) or not name.strip():
        raise DefinitionRequestError("'name' must be a non-empty string")
    if not isinstance(definition, dict):
        raise DefinitionRequestError("'definition' must be a JSON object")
    try:
        path = save_definition(config.storage_root, name, definition)
    except InvalidDefinitionNameError as exc:
        raise DefinitionRequestError(str(exc)) from exc
    return {"schema_version": WORKBENCH_API_VERSION, "name": name, "path": str(path)}


def build_load_definition_response(config: WorkbenchApiConfig, name: str) -> dict[str, Any]:
    try:
        definition = load_definition(config.storage_root, name)
    except (DefinitionNotFoundError, InvalidDefinitionNameError) as exc:
        raise DefinitionRequestError(str(exc)) from exc
    return {"schema_version": WORKBENCH_API_VERSION, "name": name, "definition": definition}
