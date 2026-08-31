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
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ResolvedPlan:
    """The concrete plan a command would execute, resolved from config alone."""

    group: str
    command: str
    workflow: str
    arguments: dict[str, Any] = field(default_factory=dict)
    output_paths: tuple[str, ...] = ()
    storage_root: str = ""
    implemented: bool = False


def render_plan_json(plan: ResolvedPlan) -> dict[str, Any]:
    """Return the machine-readable (`--json`) representation of a plan."""
    payload = asdict(plan)
    payload["output_paths"] = list(plan.output_paths)
    return payload


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
