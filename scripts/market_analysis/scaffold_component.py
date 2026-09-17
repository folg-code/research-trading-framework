"""Scaffold a new Market Analysis component.

Generates a component/implementation file skeleton, a component-contract
test stub, the registration wiring into the pack's ``__init__.py`` and
``registry/builtins.py``, and a stub entry in
``ANALYSIS_COMPONENT_CATALOG.md`` -- matching the existing hand-written
pattern in ``trading_framework.market_analysis.components`` exactly (see
e.g. ``components/structure/level_distance.py``).

Design authority: ``docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md``
D-P19-01 (ACCEPTED, maintainer, 2026-09-17). This script deliberately does
not guess a component's formula, parameter defaults or output shape -- the
author fills those in by hand. The registration and catalog patches are
simple text-anchor insertions, not an AST rewrite, per the same decision.
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

    @property
    def pack_init_file(self) -> Path:
        return self.component_file.parent / "__init__.py"

    @property
    def builtins_file(self) -> Path:
        return (
            self.repo_root
            / "src"
            / "trading_framework"
            / "market_analysis"
            / "registry"
            / "builtins.py"
        )

    @property
    def register_function_name(self) -> str:
        return f"register_{self.name}_component"

    @property
    def catalog_file(self) -> Path:
        return self.repo_root / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"


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


_MODULE_IMPORT_BLOCK_RE_TEMPLATE = (
    r"from trading_framework\.market_analysis\.components\.{pack}\.(\w+) import \(\n"
    r"((?:    \w+,\n)+)\)\n"
)
_PACK_LEVEL_IMPORT_BLOCK_RE = re.compile(
    r"from trading_framework\.market_analysis\.components\.(\w+) import \(\n"
    r"((?:    \w+,\n)+)\)\n"
)
_ALL_BLOCK_RE = re.compile(r'__all__ = \[\n((?:    "[\w.]+",\n)+)\]\n')


def _names_from_block(names_block: str) -> list[str]:
    return [line.strip().rstrip(",") for line in names_block.strip().splitlines()]


def render_pack_init(pack: str, blocks: dict[str, list[str]]) -> str:
    """Render a pack ``__init__.py`` from its (module -> class names) blocks."""
    pretty = pack.replace("_", " ").capitalize()
    lines = [f'"""{pretty}-related Market Analysis components."""', ""]
    for module in sorted(blocks):
        names = sorted(blocks[module])
        lines.append(f"from trading_framework.market_analysis.components.{pack}.{module} import (")
        lines.extend(f"    {name}," for name in names)
        lines.append(")")
    lines.append("")
    lines.append("__all__ = [")
    all_names = sorted({name for names in blocks.values() for name in names})
    lines.extend(f'    "{name}",' for name in all_names)
    lines.append("]")
    return "\n".join(lines) + "\n"


def patch_pack_init(request: ScaffoldRequest) -> str:
    """Return the new content for the pack's ``__init__.py``, module block added."""
    new_names = [request.component_class_name, request.implementation_class_name]
    if not request.pack_init_file.exists():
        return render_pack_init(request.pack, {request.name: new_names})

    text = request.pack_init_file.read_text(encoding="utf-8")
    module_re = re.compile(_MODULE_IMPORT_BLOCK_RE_TEMPLATE.format(pack=request.pack))
    blocks: dict[str, list[str]] = {
        module: _names_from_block(names_block) for module, names_block in module_re.findall(text)
    }
    if request.name in blocks:
        raise ValueError(f"{request.pack_init_file} already imports a '{request.name}' module")
    blocks[request.name] = new_names
    return render_pack_init(request.pack, blocks)


def _render_register_function(request: ScaffoldRequest) -> str:
    pretty = " ".join(word.capitalize() for word in request.name.split("_"))
    single_line = (
        f"    registry.register({request.component_class_name}(), "
        f"{request.implementation_class_name}(), default=True)"
    )
    call_body = (
        single_line
        if len(single_line) <= 100
        else (
            "    registry.register(\n"
            f"        {request.component_class_name}(),\n"
            f"        {request.implementation_class_name}(),\n"
            "        default=True,\n"
            "    )"
        )
    )
    return (
        f"def {request.register_function_name}(registry: ComponentRegistry) -> None:\n"
        f'    """Register the {pretty} component."""\n'
        f"{call_body}\n"
    )


def patch_builtins(request: ScaffoldRequest) -> str:
    """Return the new content for ``registry/builtins.py``, this component wired in."""
    text = request.builtins_file.read_text(encoding="utf-8")

    if request.component_class_name in text or request.implementation_class_name in text:
        raise ValueError(
            f"{request.builtins_file} already references "
            f"{request.component_class_name} or {request.implementation_class_name}"
        )

    # 1. Pack-level import block (from components.<pack> import (...)).
    import_matches = list(_PACK_LEVEL_IMPORT_BLOCK_RE.finditer(text))
    if not import_matches:
        raise ValueError(f"could not find any pack-level import block in {request.builtins_file}")
    pack_blocks: dict[str, list[str]] = {
        pack: _names_from_block(names_block)
        for pack, names_block in (m.groups() for m in import_matches)
    }
    new_names = {request.component_class_name, request.implementation_class_name}
    pack_blocks[request.pack] = sorted({*pack_blocks.get(request.pack, []), *new_names})
    new_import_region = "".join(
        f"from trading_framework.market_analysis.components.{pack} import (\n"
        + "".join(f"    {name},\n" for name in sorted(names))
        + ")\n"
        for pack, names in sorted(pack_blocks.items())
    )
    text = text[: import_matches[0].start()] + new_import_region + text[import_matches[-1].end() :]

    # 2. A new `register_<name>_component` function, right before `register_mvp_components`.
    function_anchor = "\n\n\ndef register_mvp_components("
    if function_anchor not in text:
        raise ValueError(f"could not find {function_anchor!r} anchor in {request.builtins_file}")
    new_function = _render_register_function(request)
    text = text.replace(
        function_anchor,
        f"\n\n\n{new_function}\n\ndef register_mvp_components(",
        1,
    )

    # 3. A call to it, at the end of `register_mvp_components`'s body.
    call_anchor = "\n\n\ndef default_mvp_registry("
    if call_anchor not in text:
        raise ValueError(f"could not find {call_anchor!r} anchor in {request.builtins_file}")
    text = text.replace(
        call_anchor,
        f"\n    {request.register_function_name}(registry){call_anchor}",
        1,
    )

    # 4. The `__all__` list, kept sorted.
    all_match = _ALL_BLOCK_RE.search(text)
    if all_match is None:
        raise ValueError(f"could not find __all__ block in {request.builtins_file}")
    existing_all = re.findall(r'"([\w.]+)"', all_match.group(1))
    combined_all = sorted({*existing_all, request.register_function_name})
    new_all_block = "__all__ = [\n" + "".join(f'    "{name}",\n' for name in combined_all) + "]\n"
    text = text[: all_match.start()] + new_all_block + text[all_match.end() :]

    return text


_CATALOG_SECTION_HEADING = "## Phase 19 additions"
_CATALOG_TODO_MARKER = "<!-- TODO: fill in before promotion -->"


def patch_catalog(request: ScaffoldRequest) -> str:
    """Return the new content for ``ANALYSIS_COMPONENT_CATALOG.md``, a stub entry added.

    Every scaffolded component's entry lands under one ``## Phase 19
    additions`` heading, created once at end-of-file on the first call and
    appended to on every later one. This assumes that heading stays the
    file's last section for as long as this tool keeps appending to it --
    true as long as nothing else is added to the catalog after it manually
    in between scaffold runs.
    """
    text = request.catalog_file.read_text(encoding="utf-8")
    if f"**`{request.component_id}`**" in text:
        raise ValueError(f"{request.catalog_file} already documents {request.component_id}")

    entry_line = f"- **`{request.component_id}`** — {_CATALOG_TODO_MARKER}"
    if not text.endswith("\n"):
        text += "\n"

    if _CATALOG_SECTION_HEADING not in text:
        return text + f"\n---\n\n{_CATALOG_SECTION_HEADING}\n\n{entry_line}\n"
    return text + f"{entry_line}\n"


def write_scaffold(request: ScaffoldRequest) -> tuple[Path, Path, Path, Path, Path]:
    """Write the component and test files, and patch the registration/catalog files.

    Refuses to touch anything if the component/test files already exist or if
    the target classes already appear in the registration files or catalog.
    """
    for path in (request.component_file, request.test_file):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {path}")

    new_pack_init = patch_pack_init(request)
    new_builtins = patch_builtins(request)
    new_catalog = patch_catalog(request)

    request.component_file.parent.mkdir(parents=True, exist_ok=True)
    request.component_file.write_text(
        render_component_file(request), encoding="utf-8", newline="\n"
    )

    request.test_file.parent.mkdir(parents=True, exist_ok=True)
    request.test_file.write_text(render_test_file(request), encoding="utf-8", newline="\n")

    request.pack_init_file.write_text(new_pack_init, encoding="utf-8", newline="\n")
    request.builtins_file.write_text(new_builtins, encoding="utf-8", newline="\n")
    request.catalog_file.write_text(new_catalog, encoding="utf-8", newline="\n")

    return (
        request.component_file,
        request.test_file,
        request.pack_init_file,
        request.builtins_file,
        request.catalog_file,
    )


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
        component_file, test_file, pack_init_file, builtins_file, catalog_file = write_scaffold(
            request
        )
    except (FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {component_file}")
    print(f"wrote {test_file}")
    print(f"patched {pack_init_file}")
    print(f"patched {builtins_file}")
    print(f"patched {catalog_file} (stub entry -- fill in before promotion)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
