"""List and apply Signal Research templates for a read-only local UI consumer.

Thin wrapper over ``trading_framework.research.signal_research.template_catalog``
(ADR-0038 section 4), matching the same shape
``application.market_data.list_published_datasets`` already uses: a narrower,
path-free summary an app like ``apps/workbench`` (which MUST NOT import
``trading_framework.research.*`` per ADR-0037 section 2) can consume through
the application layer instead.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.signal_research.template_catalog import (
    SignalResearchTemplateSummary as _ResearchTemplateSummary,
)
from trading_framework.research.signal_research.template_catalog import (
    TemplateSource,
    TemplateStatus,
)
from trading_framework.research.signal_research.template_catalog import (
    apply_signal_research_template as _apply_research_template,
)
from trading_framework.research.signal_research.template_catalog import (
    list_signal_research_templates as _list_research_templates,
)

__all__ = [
    "ApplySignalResearchTemplateRequest",
    "SignalResearchTemplateNotFoundError",
    "SignalResearchTemplateSummary",
    "TemplateSource",
    "TemplateStatus",
    "apply_signal_research_template",
    "list_signal_research_templates",
]


class SignalResearchTemplateNotFoundError(ValidationError):
    """Raised when no SUPPORTED template matches the requested `template_id`."""


@dataclass(frozen=True, slots=True)
class SignalResearchTemplateSummary:
    """Read-only summary of one template, safe to expose to a local UI.

    Deliberately narrower than the research-layer summary: no filesystem
    path, matching the workbench API's "no filesystem path the operator did
    not supply" rule (ADR-0037 section 4).
    """

    template_id: str
    template_version: int | None
    title: str | None
    description: str | None
    source: TemplateSource
    status: TemplateStatus
    reason: str | None
    unresolvable_model_aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ApplySignalResearchTemplateRequest:
    """Apply the SUPPORTED template named `template_id`, merging `overrides`."""

    template_id: str
    overrides: Mapping[str, Any]


def list_signal_research_templates(
    user_templates_root: Path | None = None,
) -> tuple[SignalResearchTemplateSummary, ...]:
    """List framework templates, then user templates, applying the collision rule."""
    return tuple(
        _to_application_summary(summary)
        for summary in _list_research_templates(user_templates_root)
    )


def apply_signal_research_template(
    request: ApplySignalResearchTemplateRequest,
    *,
    user_templates_root: Path | None = None,
) -> dict[str, Any]:
    """Merge the named template's definition body with operator overrides.

    Returns a plain payload dict -- **not yet** a validated
    ``SignalResearchDefinitionSpec`` (ADR-0038 section 1: the caller
    validates it, this never reimplements validation).
    """
    research_summary = _find_research_summary(request.template_id, user_templates_root)
    return _apply_research_template(research_summary, overrides=request.overrides)


def _find_research_summary(
    template_id: str, user_templates_root: Path | None
) -> _ResearchTemplateSummary:
    matches = [
        summary
        for summary in _list_research_templates(user_templates_root)
        if summary.template_id == template_id
    ]
    if not matches:
        msg = f"no template found with template_id={template_id!r}"
        raise SignalResearchTemplateNotFoundError(msg)
    supported = next(
        (summary for summary in matches if summary.status is TemplateStatus.SUPPORTED), None
    )
    if supported is not None:
        return supported
    # A collision leaves the user copy SHADOWED, not silently dropped -- the
    # first match's own reason (e.g. why it is SHADOWED or UNSUPPORTED) is
    # exactly what the caller needs to see.
    first = matches[0]
    msg = f"template {template_id!r} is not applicable ({first.status.value}): {first.reason}"
    raise SignalResearchTemplateNotFoundError(msg)


def _to_application_summary(
    summary: _ResearchTemplateSummary,
) -> SignalResearchTemplateSummary:
    return SignalResearchTemplateSummary(
        template_id=summary.template_id,
        template_version=summary.template_version,
        title=summary.title,
        description=summary.description,
        source=summary.source,
        status=summary.status,
        reason=summary.reason,
        unresolvable_model_aliases=summary.unresolvable_model_aliases,
    )
