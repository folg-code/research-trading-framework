"""Template list/apply endpoint bodies (Sprint 064 T008, ADR-0038 section 4).

Transport-independent by design, same pattern as `datasets_endpoint.py`:
builds plain JSON-serializable payloads from
`trading_framework.application.signal_research`'s template wrapper (never
the research-layer catalog directly -- `workbench_core` MUST NOT import
`trading_framework.research.*`, ADR-0037 section 2).
"""

from __future__ import annotations

from typing import Any

from trading_framework.application.signal_research import (
    ApplySignalResearchTemplateRequest,
    SignalResearchTemplateNotFoundError,
    SignalResearchTemplateSummary,
    apply_signal_research_template,
    list_signal_research_templates,
)

from workbench_core.api_version import WORKBENCH_API_VERSION
from workbench_core.config import WorkbenchApiConfig


class TemplateRequestError(ValueError):
    """Raised for a malformed or inapplicable template request."""


def build_templates_response(config: WorkbenchApiConfig) -> dict[str, Any]:
    """Build the `GET /api/v1/templates` response body: every listed template.

    `config` is accepted for parity with `build_datasets_response` and to
    keep the signature stable once an operator-configured user-templates
    root exists (no such config key exists yet this sprint -- framework
    templates only).
    """
    del config
    summaries = list_signal_research_templates()
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "templates": [_summary_to_json(summary) for summary in summaries],
    }


def build_apply_template_response(
    config: WorkbenchApiConfig, template_id: str, body: dict[str, Any]
) -> dict[str, Any]:
    del config
    overrides = body.get("overrides", {})
    if not isinstance(overrides, dict):
        raise TemplateRequestError("'overrides' must be a JSON object")
    try:
        definition = apply_signal_research_template(
            ApplySignalResearchTemplateRequest(template_id=template_id, overrides=overrides)
        )
    except SignalResearchTemplateNotFoundError as exc:
        raise TemplateRequestError(str(exc)) from exc
    return {"schema_version": WORKBENCH_API_VERSION, "definition": definition}


def _summary_to_json(summary: SignalResearchTemplateSummary) -> dict[str, Any]:
    return {
        "template_id": summary.template_id,
        "template_version": summary.template_version,
        "title": summary.title,
        "description": summary.description,
        "source": summary.source.value,
        "status": summary.status.value,
        "reason": summary.reason,
        "unresolvable_model_aliases": list(summary.unresolvable_model_aliases),
    }
