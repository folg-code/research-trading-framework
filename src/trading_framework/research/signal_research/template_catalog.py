"""Framework-owned and user-authored Signal Research templates (ADR-0038 section 4).

A template is **data**: a partial ``SignalResearchDefinitionSpec`` payload
plus presentation metadata (``template_id``, ``template_version``, ``title``,
``description``). Listing never imports a Python file, executes model code,
or resolves a model beyond checking whether a declared alias is a known
built-in (ADR-0038 section 4, ADR-0039 section 4) -- it only reads YAML.

Two roots, framework wins on a ``template_id`` collision (D-S064-06):

    src/trading_framework/research/signal_research/templates/*.yaml
        framework-owned, version-controlled, ships with a fork

    user_data/config/signal_research/templates/*.yaml   (caller-supplied path)
        operator-owned, discovered and listed as USER
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

import yaml  # type: ignore[import-untyped]

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.signal_research.model_registry import (
    is_known_market_model_alias,
    is_known_signal_model_alias,
)

_FRAMEWORK_TEMPLATES_DIR: Final = Path(__file__).resolve().parent / "templates"
_REQUIRED_TOP_LEVEL_KEYS: Final = frozenset(
    {"template_id", "template_version", "title", "description", "definition"}
)


class TemplateApplicationError(ValidationError):
    """Raised when a template cannot be applied (not SUPPORTED)."""


class TemplateSource(StrEnum):
    """Where a listed template came from."""

    FRAMEWORK = "FRAMEWORK"
    USER = "USER"


class TemplateStatus(StrEnum):
    """A listed template's usability, never hidden regardless of value."""

    SUPPORTED = "SUPPORTED"
    SHADOWED = "SHADOWED"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class SignalResearchTemplateSummary:
    """One listed template. Never carries an opened model or executed code."""

    template_id: str
    template_version: int | None
    title: str | None
    description: str | None
    source: TemplateSource
    status: TemplateStatus
    path: Path
    reason: str | None = None
    unresolvable_model_aliases: tuple[str, ...] = ()


def list_signal_research_templates(
    user_templates_root: Path | None = None,
) -> tuple[SignalResearchTemplateSummary, ...]:
    """List framework templates, then user templates, applying the collision rule.

    Framework wins on a ``template_id`` collision: the framework entry stays
    ``SUPPORTED``, the colliding user entry is listed as ``SHADOWED`` --
    visible, never silently dropped, never silently applied instead. A
    malformed user template is listed ``UNSUPPORTED`` with its parse error;
    one bad file never breaks the listing for every other template.
    """
    framework_summaries = [
        _load_template(path, source=TemplateSource.FRAMEWORK)
        for path in sorted(_FRAMEWORK_TEMPLATES_DIR.glob("*.yaml"))
    ]
    framework_ids = {
        summary.template_id
        for summary in framework_summaries
        if summary.status is not TemplateStatus.UNSUPPORTED
    }

    user_summaries: list[SignalResearchTemplateSummary] = []
    if user_templates_root is not None and user_templates_root.is_dir():
        for path in sorted(user_templates_root.glob("*.yaml")):
            summary = _load_template(path, source=TemplateSource.USER)
            if summary.status is not TemplateStatus.UNSUPPORTED and (
                summary.template_id in framework_ids
            ):
                summary = _shadowed(summary)
            user_summaries.append(summary)

    return tuple(framework_summaries + user_summaries)


def apply_signal_research_template(
    summary: SignalResearchTemplateSummary,
    *,
    overrides: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge a ``SUPPORTED`` template's definition body with operator overrides.

    Returns a plain payload dict -- **not yet** a validated
    ``SignalResearchDefinitionSpec``. The caller passes the result to
    ``SignalResearchDefinitionSpec.from_dict()`` to validate it, exactly like
    any other definition file (ADR-0038 section 1: the template never
    reimplements validation). Applying a ``SHADOWED`` or ``UNSUPPORTED``
    template is refused -- pick the framework original, or fix the malformed
    file, first.
    """
    if summary.status is not TemplateStatus.SUPPORTED:
        msg = (
            f"cannot apply a {summary.status.value} template "
            f"({summary.template_id!r}): {summary.reason}"
        )
        raise TemplateApplicationError(msg)
    raw = yaml.safe_load(summary.path.read_text(encoding="utf-8"))
    definition = dict(raw["definition"])
    definition.update(overrides)
    return definition


def _shadowed(summary: SignalResearchTemplateSummary) -> SignalResearchTemplateSummary:
    reason = (
        f"shadowed by the framework template with the same template_id "
        f"({summary.template_id!r}); rename this template_id to select it"
    )
    return SignalResearchTemplateSummary(
        template_id=summary.template_id,
        template_version=summary.template_version,
        title=summary.title,
        description=summary.description,
        source=summary.source,
        status=TemplateStatus.SHADOWED,
        path=summary.path,
        reason=reason,
        unresolvable_model_aliases=summary.unresolvable_model_aliases,
    )


def _unsupported(
    path: Path, *, source: TemplateSource, reason: str, raw: dict[str, Any] | None = None
) -> SignalResearchTemplateSummary:
    raw = raw or {}
    return SignalResearchTemplateSummary(
        template_id=str(raw.get("template_id") or path.stem),
        template_version=_optional_int(raw.get("template_version")),
        title=_optional_str(raw.get("title")),
        description=_optional_str(raw.get("description")),
        source=source,
        status=TemplateStatus.UNSUPPORTED,
        path=path,
        reason=reason,
    )


def _load_template(path: Path, *, source: TemplateSource) -> SignalResearchTemplateSummary:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return _unsupported(path, source=source, reason=f"failed to parse: {exc}")

    if not isinstance(raw, dict):
        return _unsupported(path, source=source, reason="template root must be a mapping")

    missing = _REQUIRED_TOP_LEVEL_KEYS - raw.keys()
    if missing:
        return _unsupported(
            path,
            source=source,
            reason=f"missing required key(s): {', '.join(sorted(missing))}",
            raw=raw,
        )

    definition = raw["definition"]
    if not isinstance(definition, dict):
        return _unsupported(path, source=source, reason="'definition' must be a mapping", raw=raw)

    try:
        template_version = int(raw["template_version"])
    except (TypeError, ValueError):
        return _unsupported(
            path, source=source, reason="'template_version' must be an integer", raw=raw
        )

    return SignalResearchTemplateSummary(
        template_id=str(raw["template_id"]),
        template_version=template_version,
        title=str(raw["title"]),
        description=str(raw["description"]),
        source=source,
        status=TemplateStatus.SUPPORTED,
        path=path,
        unresolvable_model_aliases=_unresolvable_model_aliases(definition),
    )


def _unresolvable_model_aliases(definition: dict[str, Any]) -> tuple[str, ...]:
    unresolvable: list[str] = []
    market_model = definition.get("market_model")
    if isinstance(market_model, str) and not is_known_market_model_alias(market_model):
        unresolvable.append(market_model)
    signal_model = definition.get("signal_model")
    if isinstance(signal_model, str) and not is_known_signal_model_alias(signal_model):
        unresolvable.append(signal_model)
    return tuple(unresolvable)


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
