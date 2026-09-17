"""Scaffold a new Market Analysis component.

Generates a component/implementation file skeleton and a component-contract
test stub, matching the existing hand-written registration pattern in
``trading_framework.market_analysis.components`` exactly (see e.g.
``components/structure/level_distance.py``). Registration wiring into
``registry/builtins.py`` and a catalog-doc stub are separate, later pieces
of this same tool (Phase 19 Sprint 065 T002/T003) -- not implemented here.

Design authority: ``docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md``
D-P19-01 (ACCEPTED, maintainer, 2026-09-17). This script deliberately does
not guess a component's formula, parameter defaults or output shape -- the
author fills those in by hand.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_COMPONENT_ID_PATTERN = re.compile(r"^(?P<pack>[a-z][a-z0-9_]*)\.(?P<name>[a-z][a-z0-9_]*)$")
_VALID_KINDS = ("feature", "structure", "state")
_CAUSAL_ONLY_PACKS = frozenset({"session"})


@dataclass(frozen=True)
class ScaffoldRequest:
    """Fully resolved, validated inputs for one scaffolded component."""

    component_id: str
    pack: str
    name: str
    kind: str
    causal: bool
    depends_on: tuple[str, ...]
    repo_root: Path

    @property
    def class_stem(self) -> str:
        return "".join(part.capitalize() for part in self.name.split("_"))

    @property
    def component_class_name(self) -> str:
        return f"{self.class_stem}Component"

    @property
    def implementation_class_name(self) -> str:
        return f"Numpy{self.class_stem}Implementation"

    @property
    def implementation_id_value(self) -> str:
        return f"numpy.{self.name}"

    @property
    def kind_enum_member(self) -> str:
        return self.kind.upper()

    @property
    def causality_enum_member(self) -> str:
        return "CAUSAL" if self.causal else "DELAYED"

    @property
    def component_file(self) -> Path:
        return (
            self.repo_root
            / "src"
            / "trading_framework"
            / "market_analysis"
            / "components"
            / self.pack
            / f"{self.name}.py"
        )

    @property
    def test_file(self) -> Path:
        return self.repo_root / "tests" / "unit" / "market_analysis" / f"test_{self.name}.py"


def _parse_component_id(component_id: str, pack_arg: str | None) -> tuple[str, str]:
    match = _COMPONENT_ID_PATTERN.fullmatch(component_id.strip())
    if match is None:
        raise ValueError(
            f"invalid --component-id {component_id!r}: expected exactly "
            "'<pack>.<name>', both lowercase snake_case (e.g. 'structure.opening_gap')"
        )
    pack, name = match.group("pack"), match.group("name")
    if pack_arg is not None and pack_arg != pack:
        raise ValueError(
            f"--pack {pack_arg!r} does not match the component id's own pack prefix {pack!r}"
        )
    return pack, name


def build_request(args: argparse.Namespace) -> ScaffoldRequest:
    """Validate CLI arguments and resolve them into a :class:`ScaffoldRequest`."""
    pack, name = _parse_component_id(args.component_id, args.pack)
    if pack in _CAUSAL_ONLY_PACKS and not args.causal:
        raise ValueError(
            f"pack {pack!r} components must stay causal-only "
            "(binding rule, PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md); "
            "--no-causal is refused for this pack"
        )
    return ScaffoldRequest(
        component_id=args.component_id,
        pack=pack,
        name=name,
        kind=args.kind,
        causal=args.causal,
        depends_on=tuple(args.depends_on or ()),
        repo_root=Path(args.repo_root).resolve(),
    )


def render_component_file(request: ScaffoldRequest) -> str:
    """Render the component/implementation module skeleton."""
    all_entries = ", ".join(
        f'"{name}"'
        for name in sorted((request.component_class_name, request.implementation_class_name))
    )
    depends_on_comment = ""
    if request.depends_on:
        bullet_lines = "\n".join(f"        #   - {dep}" for dep in request.depends_on)
        depends_on_comment = (
            "\n        # TODO: wire up ComponentDependency entries for:\n"
            f"{bullet_lines}\n"
            "        # (see structure.level_distance for the pattern)"
        )

    return f'''"""{request.component_class_name} Market Analysis component.

TODO: replace this stub with the real formula, parameter schema and output
shape before promotion (ANALYSIS_COMPONENT_CATALOG.md entry required).
"""

from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
    ImplementationId,
    ImplementationVersion,
)
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import OutputSchema
from trading_framework.market_analysis.models.parameters import CanonicalParameters, ParameterSchema
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView

_COMPONENT_ID = ComponentId("{request.component_id}")
_COMPONENT_VERSION = ComponentVersion("1.0.0")
_IMPLEMENTATION_ID = ImplementationId("{request.implementation_id_value}")
_IMPLEMENTATION_VERSION = ImplementationVersion("1.0.0")

# TODO: replace with the real output field id(s), e.g. OutputId("value").
_PARAMETER_SCHEMA = ParameterSchema(fields=())
_OUTPUT_SCHEMA = OutputSchema(outputs=())


class {request.component_class_name}:
    """TODO: one-line summary, then the formula and warm-up/zero-denominator convention."""

    component_id = _COMPONENT_ID
    component_version = _COMPONENT_VERSION
    kind = ComponentKind.{request.kind_enum_member}
    causality = Causality.{request.causality_enum_member}
    parameter_schema = _PARAMETER_SCHEMA
    output_schema = _OUTPUT_SCHEMA

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        raise NotImplementedError("TODO: declare bars_before for this component")

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        raise NotImplementedError("TODO: declare required raw OHLCV fields")

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:{depends_on_comment}
        raise NotImplementedError("TODO: declare component dependencies, if any")


class {request.implementation_class_name}:
    """TODO: one-line summary of the NumPy backend."""

    implementation_id = _IMPLEMENTATION_ID
    implementation_version = _IMPLEMENTATION_VERSION

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        raise NotImplementedError("TODO: implement the real computation")


__all__ = [{all_entries}]
'''


def render_test_file(request: ScaffoldRequest) -> str:
    """Render the component-contract test stub."""
    import_names = ",\n    ".join(
        sorted((request.component_class_name, request.implementation_class_name))
    )
    return f'''"""Contract test stub for the ``{request.component_id}`` component.

Generated by ``scripts/market_analysis/scaffold_component.py``. Fill in real
behavioral tests once the component's formula and output shape are
implemented -- these two tests only check identity and registration.
"""

from trading_framework.market_analysis.components.{request.pack}.{request.name} import (
    {import_names},
)
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.registry.registry import ComponentRegistry


def test_{request.name}_component_declares_identity() -> None:
    component = {request.component_class_name}()
    assert component.component_id == ComponentId("{request.component_id}")
    assert component.kind is ComponentKind.{request.kind_enum_member}
    assert component.causality is Causality.{request.causality_enum_member}


def test_{request.name}_component_registers() -> None:
    registry = ComponentRegistry()
    registry.register(
        {request.component_class_name}(),
        {request.implementation_class_name}(),
        default=True,
    )
    assert registry.get_component(ComponentId("{request.component_id}")) is not None
'''


def write_scaffold(request: ScaffoldRequest) -> tuple[Path, Path]:
    """Write the component and test files. Refuses to overwrite either."""
    for path in (request.component_file, request.test_file):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {path}")

    request.component_file.parent.mkdir(parents=True, exist_ok=True)
    request.component_file.write_text(
        render_component_file(request), encoding="utf-8", newline="\n"
    )

    request.test_file.parent.mkdir(parents=True, exist_ok=True)
    request.test_file.write_text(render_test_file(request), encoding="utf-8", newline="\n")

    return request.component_file, request.test_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scaffold_component",
        description=(
            "Scaffold a new Market Analysis component's file skeleton and "
            "component-contract test stub."
        ),
    )
    parser.add_argument(
        "--component-id",
        required=True,
        help="e.g. 'structure.opening_gap' -- must be '<pack>.<name>', both lowercase snake_case",
    )
    parser.add_argument(
        "--pack",
        default=None,
        help="component pack (e.g. 'structure'); must match --component-id's prefix if given",
    )
    parser.add_argument(
        "--kind",
        choices=_VALID_KINDS,
        default="feature",
        help="ComponentKind value (default: feature)",
    )
    parser.add_argument(
        "--causal",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="causality declaration; --no-causal is refused for session.* components",
    )
    parser.add_argument(
        "--depends-on",
        action="append",
        default=None,
        metavar="COMPONENT_ID",
        help="a dependency component id (repeatable); left as a TODO comment, not wired up",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd()),
        help="repository root to scaffold into (default: current working directory)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        request = build_request(args)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        component_file, test_file = write_scaffold(request)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {component_file}")
    print(f"wrote {test_file}")
    print(
        "Registration into registry/builtins.py and the "
        "ANALYSIS_COMPONENT_CATALOG.md stub are not yet automated "
        "(Phase 19 Sprint 065 T002/T003) -- wire this component in by hand for now."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
