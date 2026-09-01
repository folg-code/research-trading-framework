"""Resolved-plan model and renderers for `--dry-run` / `--json` (D-S046-04, D-S046-09).

Every command resolves a `ResolvedPlan` from the validated config *before* it
touches anything (Sprint Goal diagram, `SPRINT_046.md` §1). `--dry-run` prints
that plan and stops -- no file write, no dataset registration, nothing.

The JSON shape is deliberately structured (not a formatted string) so that a
later consumer (S046-T006: composing `research run predictive`) can read
identifiers from a typed field rather than parsing stdout text -- the CLI
never round-trips an identifier through printed output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResolvedPlan:
    """The concrete plan a command would execute, resolved from config alone.

    ``runtime_context`` (S047-T003) carries typed, in-process objects a
    command's own `run()` needs but that must never be serialized or printed
    -- e.g. an already-loaded `StrategyModelDefinition` (ADR-0027 Sec4: loaded
    exactly once, during `resolve_plan`, so both `--dry-run` and an actual run
    share the single pre-flight load). It is deliberately excluded from
    `render_plan_text`/`render_plan_json`.
    """

    group: str
    command: str
    workflow: str
    arguments: dict[str, Any] = field(default_factory=dict)
    output_paths: tuple[str, ...] = ()
    storage_root: str = ""
    implemented: bool = False
    runtime_context: dict[str, Any] = field(default_factory=dict)


def render_plan_json(plan: ResolvedPlan) -> dict[str, Any]:
    """Return the machine-readable (`--json`) representation of a plan.

    ``runtime_context`` is intentionally omitted: it holds in-process objects
    (not config-derived data) that are neither JSON-serializable nor part of
    the operator-facing plan contract.
    """
    return {
        "group": plan.group,
        "command": plan.command,
        "workflow": plan.workflow,
        "arguments": dict(plan.arguments),
        "output_paths": list(plan.output_paths),
        "storage_root": plan.storage_root,
        "implemented": plan.implemented,
    }


def render_plan_text(plan: ResolvedPlan) -> str:
    """Return the human-readable representation of a plan."""
    lines = [
        f"group:         {plan.group}",
        f"command:       {plan.command}",
        f"workflow:      {plan.workflow}",
        f"storage_root:  {plan.storage_root}",
        "arguments:",
    ]
    if plan.arguments:
        for key, value in sorted(plan.arguments.items()):
            lines.append(f"  {key}: {value}")
    else:
        lines.append("  (none)")
    lines.append("output_paths:")
    if plan.output_paths:
        for output_path in plan.output_paths:
            lines.append(f"  {output_path}")
    else:
        lines.append("  (none)")
    if not plan.implemented:
        lines.append("note:          this command is not implemented yet (Wave 1 skeleton)")
    return "\n".join(lines)


def dump_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)
