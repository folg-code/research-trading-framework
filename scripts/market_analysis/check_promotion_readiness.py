"""Report promotion readiness for Market Analysis components -- read-only.

Checks the six mechanical criteria D-P19-01 lists (registered, tested,
output schema non-empty, dependency declaration present, catalog entry
present without the TODO marker, causal-only gate for ``session.*``
components) and prints a PASS / FAIL / NEEDS-REVIEW / N/A table, one row
per check per component.

This tool recommends; it never promotes, registers, or edits any file --
per IDEA-011's own "Important Rule" (a recommendation surface, not an
auto-promoter). It is not a CI gate.

Design authority: ``docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md``
D-P19-01 (ACCEPTED, maintainer, 2026-09-17).
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from trading_framework.core.exceptions import ConfigurationError, ValidationError
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.kind import Causality
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry

_CATALOG_TODO_MARKER = "<!-- TODO: fill in before promotion -->"
_CAUSAL_ONLY_PACK = "session"
_SUSPICIOUS_FULL_PERIOD_PHRASES = (
    "full period",
    "full_period",
    "entire period",
    "entire session",
    "final high",
    "final low",
)


class Verdict(Enum):
    """One check's outcome. Never used to auto-promote or block anything."""

    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS-REVIEW"
    NOT_APPLICABLE = "N/A"


@dataclass(frozen=True)
class CheckResult:
    name: str
    verdict: Verdict
    detail: str


def _component_name(component_id: str) -> str | None:
    parts = component_id.split(".", 1)
    return parts[1] if len(parts) == 2 else None


def _test_file(repo_root: Path, component_id: str) -> Path | None:
    name = _component_name(component_id)
    if name is None:
        return None
    return repo_root / "tests" / "unit" / "market_analysis" / f"test_{name}.py"


def _catalog_file(repo_root: Path) -> Path:
    return repo_root / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"


def check_registered(
    component_id: str, registry: ComponentRegistry
) -> tuple[CheckResult, BatchAnalysisComponent | None]:
    try:
        parsed_id = ComponentId(component_id)
    except ValidationError as exc:
        return CheckResult("registered", Verdict.FAIL, f"invalid component id: {exc}"), None
    try:
        component = registry.get_component(parsed_id)
    except ConfigurationError:
        return (
            CheckResult("registered", Verdict.FAIL, "not registered in default_mvp_registry()"),
            None,
        )
    return CheckResult("registered", Verdict.PASS, "registered"), component


def check_tested(repo_root: Path, component_id: str) -> CheckResult:
    path = _test_file(repo_root, component_id)
    if path is None:
        return CheckResult("tested", Verdict.FAIL, f"invalid component id: {component_id!r}")
    if not path.is_file():
        return CheckResult("tested", Verdict.FAIL, f"no test file at {path}")
    text = path.read_text(encoding="utf-8")
    if not re.search(r"^def test_", text, re.MULTILINE):
        return CheckResult("tested", Verdict.FAIL, f"{path} defines no test_ function")
    return CheckResult("tested", Verdict.PASS, f"{path} defines at least one test")


def check_catalog_entry(repo_root: Path, component_id: str) -> CheckResult:
    path = _catalog_file(repo_root)
    if not path.is_file():
        return CheckResult("catalog_entry", Verdict.FAIL, f"catalog file not found: {path}")
    text = path.read_text(encoding="utf-8")
    needle = f"`{component_id}`"
    if needle not in text:
        return CheckResult("catalog_entry", Verdict.FAIL, f"no entry for {component_id} in {path}")
    entry_line = next((line for line in text.splitlines() if needle in line), "")
    if _CATALOG_TODO_MARKER in entry_line:
        return CheckResult("catalog_entry", Verdict.FAIL, "entry still carries the TODO marker")
    return CheckResult("catalog_entry", Verdict.PASS, "documented, no TODO marker")


def check_output_schema(component: BatchAnalysisComponent) -> CheckResult:
    outputs = component.output_schema.outputs
    if not outputs:
        return CheckResult("output_schema", Verdict.FAIL, "OutputSchema has no fields")
    return CheckResult("output_schema", Verdict.PASS, f"{len(outputs)} output field(s)")


def check_dependencies_declared(component: BatchAnalysisComponent) -> CheckResult:
    try:
        parameters = component.parameter_schema.canonicalize({})
    except ValidationError as exc:
        return CheckResult(
            "dependencies_declared",
            Verdict.NEEDS_REVIEW,
            f"could not canonicalize default parameters to check: {exc}",
        )
    try:
        component.data_dependencies(parameters)
        component.component_dependencies(parameters)
    except NotImplementedError:
        return CheckResult(
            "dependencies_declared", Verdict.FAIL, "still raises NotImplementedError"
        )
    except Exception as exc:  # reporting-only tool, must not crash on odd component behavior
        return CheckResult(
            "dependencies_declared",
            Verdict.NEEDS_REVIEW,
            f"raised unexpectedly with default parameters: {exc}",
        )
    return CheckResult("dependencies_declared", Verdict.PASS, "both methods implemented")


def check_causal_only_gate(component_id: str, component: BatchAnalysisComponent) -> CheckResult:
    pack = component_id.split(".", 1)[0]
    if pack != _CAUSAL_ONLY_PACK:
        return CheckResult(
            "causal_only_gate", Verdict.NOT_APPLICABLE, f"not a {_CAUSAL_ONLY_PACK}.* component"
        )
    if component.causality is not Causality.CAUSAL:
        return CheckResult(
            "causal_only_gate",
            Verdict.FAIL,
            f"causality is {component.causality.value}, must be causal",
        )
    docstring = (type(component).__doc__ or "").lower()
    output_ids = " ".join(field.output_id.value for field in component.output_schema.outputs)
    haystack = f"{docstring} {output_ids.lower()}"
    hits = [phrase for phrase in _SUSPICIOUS_FULL_PERIOD_PHRASES if phrase in haystack]
    if hits:
        return CheckResult(
            "causal_only_gate",
            Verdict.NEEDS_REVIEW,
            f"causal, but docstring/output names mention: {', '.join(hits)} "
            "-- verify no look-ahead",
        )
    return CheckResult("causal_only_gate", Verdict.PASS, "causal, no suspicious language found")


def run_checks(
    component_id: str, repo_root: Path, registry: ComponentRegistry
) -> list[CheckResult]:
    """Run all six checks for one component id. Never mutates any file."""
    registered_result, component = check_registered(component_id, registry)
    results = [
        registered_result,
        check_tested(repo_root, component_id),
        check_catalog_entry(repo_root, component_id),
    ]
    if component is None:
        results.extend(
            CheckResult(name, Verdict.NOT_APPLICABLE, "component not registered")
            for name in ("output_schema", "dependencies_declared", "causal_only_gate")
        )
        return results
    results.append(check_output_schema(component))
    results.append(check_dependencies_declared(component))
    results.append(check_causal_only_gate(component_id, component))
    return results


def render_table(reports: dict[str, list[CheckResult]]) -> str:
    lines = []
    for component_id, results in reports.items():
        lines.append(f"# {component_id}")
        for result in results:
            lines.append(f"  [{result.verdict.value:^12}] {result.name}: {result.detail}")
    return "\n".join(lines)


def render_markdown(reports: dict[str, list[CheckResult]]) -> str:
    lines = ["| Component | Check | Verdict | Detail |", "|---|---|---|---|"]
    for component_id, results in reports.items():
        for result in results:
            lines.append(
                f"| `{component_id}` | {result.name} | {result.verdict.value} | {result.detail} |"
            )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_promotion_readiness",
        description=(
            "Report promotion readiness for one or more Market Analysis "
            "components. Read-only: never registers, promotes, or edits anything."
        ),
    )
    parser.add_argument(
        "--component-id",
        action="append",
        required=True,
        metavar="COMPONENT_ID",
        help="a component id to check (repeatable)",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd()),
        help="repository root to check test/catalog files against (default: cwd)",
    )
    parser.add_argument(
        "--markdown-out",
        default=None,
        metavar="PATH",
        help="also write a markdown table to this path, for pasting into a PR description",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    registry = default_mvp_registry()

    reports = {
        component_id: run_checks(component_id, repo_root, registry)
        for component_id in args.component_id
    }

    print(render_table(reports))

    if args.markdown_out is not None:
        Path(args.markdown_out).write_text(render_markdown(reports), encoding="utf-8", newline="\n")
        print(f"\nwrote {args.markdown_out}")

    any_failed = any(
        result.verdict is Verdict.FAIL for results in reports.values() for result in results
    )
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
