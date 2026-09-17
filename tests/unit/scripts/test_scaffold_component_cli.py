"""CLI tests for scripts/market_analysis/scaffold_component.py (Sprint 065 T001-T003)."""

import ast
from pathlib import Path

import pytest
from scripts.market_analysis import scaffold_component

_BUILTINS_SEED = '''"""Built-in Market Analysis component registration."""

from trading_framework.market_analysis.components.structure import (
    LevelDistanceComponent,
    NumpyLevelDistanceImplementation,
)
from trading_framework.market_analysis.registry.registry import ComponentRegistry


def register_level_distance_component(registry: ComponentRegistry) -> None:
    """Register the Level Distance structure component."""
    registry.register(
        LevelDistanceComponent(),
        NumpyLevelDistanceImplementation(),
        default=True,
    )


def register_mvp_components(registry: ComponentRegistry) -> None:
    """Register Sprint 003 MVP feature and state components."""
    register_level_distance_component(registry)


def default_mvp_registry() -> ComponentRegistry:
    """Return a registry with all MVP components registered."""
    registry = ComponentRegistry()
    register_mvp_components(registry)
    return registry


__all__ = [
    "default_mvp_registry",
    "register_level_distance_component",
    "register_mvp_components",
]
'''

_STRUCTURE_INIT_SEED = '''"""Structure-related Market Analysis components."""

from trading_framework.market_analysis.components.structure.level_distance import (
    LevelDistanceComponent,
    NumpyLevelDistanceImplementation,
)

__all__ = [
    "LevelDistanceComponent",
    "NumpyLevelDistanceImplementation",
]
'''

_CATALOG_SEED = """# Analysis Component Catalog

## Sprint 003 additions

- **`structure.level_distance`** -- ATR-normalized distance to session high/low.
"""


def _seed_registry(repo_root: Path) -> None:
    """Seed a minimal, structurally realistic registry to scaffold against."""
    builtins_file = (
        repo_root / "src" / "trading_framework" / "market_analysis" / "registry" / "builtins.py"
    )
    builtins_file.parent.mkdir(parents=True, exist_ok=True)
    builtins_file.write_text(_BUILTINS_SEED, encoding="utf-8")

    structure_init = (
        repo_root
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "__init__.py"
    )
    structure_init.parent.mkdir(parents=True, exist_ok=True)
    structure_init.write_text(_STRUCTURE_INIT_SEED, encoding="utf-8")

    catalog_file = repo_root / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    catalog_file.write_text(_CATALOG_SEED, encoding="utf-8")


def test_scaffold_writes_component_and_test_files(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--pack",
            "structure",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    component_file = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "opening_gap.py"
    )
    test_file = tmp_path / "tests" / "unit" / "market_analysis" / "test_opening_gap.py"
    assert component_file.is_file()
    assert test_file.is_file()

    component_source = component_file.read_text(encoding="utf-8")
    ast.parse(component_source)  # syntactically valid Python
    assert "class OpeningGapComponent:" in component_source
    assert "class NumpyOpeningGapImplementation:" in component_source
    assert 'ComponentId("structure.opening_gap")' in component_source
    assert 'ImplementationId("numpy.opening_gap")' in component_source
    assert "ComponentKind.FEATURE" in component_source
    assert "Causality.CAUSAL" in component_source
    assert "raise NotImplementedError" in component_source

    test_source = test_file.read_text(encoding="utf-8")
    ast.parse(test_source)
    assert "def test_opening_gap_component_declares_identity" in test_source
    assert "def test_opening_gap_component_registers" in test_source
    assert "OpeningGapComponent" in test_source
    assert "NumpyOpeningGapImplementation" in test_source


def test_scaffold_patches_pack_init_and_builtins(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0

    structure_init = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "__init__.py"
    )
    init_source = structure_init.read_text(encoding="utf-8")
    ast.parse(init_source)
    assert "from trading_framework.market_analysis.components.structure.opening_gap import (" in (
        init_source
    )
    assert "OpeningGapComponent" in init_source
    assert "NumpyOpeningGapImplementation" in init_source
    # Existing module block must survive untouched.
    assert "LevelDistanceComponent" in init_source
    assert init_source.count("__all__ = [") == 1

    builtins_file = (
        tmp_path / "src" / "trading_framework" / "market_analysis" / "registry" / "builtins.py"
    )
    builtins_source = builtins_file.read_text(encoding="utf-8")
    ast.parse(builtins_source)
    assert "def register_opening_gap_component(registry: ComponentRegistry) -> None:" in (
        builtins_source
    )
    assert "register_opening_gap_component(registry)" in builtins_source
    assert '"register_opening_gap_component"' in builtins_source
    # Existing registration must survive untouched.
    assert "register_level_distance_component(registry)" in builtins_source
    assert builtins_source.count("__all__ = [") == 1

    # register_opening_gap_component's call must land inside register_mvp_components,
    # i.e. before default_mvp_registry is defined.
    call_index = builtins_source.index("register_opening_gap_component(registry)\n")
    mvp_def_index = builtins_source.index("def register_mvp_components(")
    default_def_index = builtins_source.index("def default_mvp_registry(")
    assert mvp_def_index < call_index < default_def_index


def test_scaffold_appends_catalog_stub_entry(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0

    catalog_file = tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_source = catalog_file.read_text(encoding="utf-8")
    assert "## Phase 19 additions" in catalog_source
    assert "`structure.opening_gap`" in catalog_source
    assert "<!-- TODO: fill in before promotion -->" in catalog_source
    # Existing content must survive untouched.
    assert "`structure.level_distance`" in catalog_source
    assert catalog_source.count("## Phase 19 additions") == 1


def test_scaffold_appends_second_entry_to_existing_phase19_section(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    first = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert first == 0
    second = scaffold_component.main(
        [
            "--component-id",
            "structure.range_discontinuity",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert second == 0

    catalog_source = (
        tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    ).read_text(encoding="utf-8")
    assert catalog_source.count("## Phase 19 additions") == 1
    assert "`structure.opening_gap`" in catalog_source
    assert "`structure.range_discontinuity`" in catalog_source


def test_scaffold_refuses_when_catalog_already_documents_component_id(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    catalog_file = tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_file.write_text(
        catalog_file.read_text(encoding="utf-8")
        + "\n## Phase 19 additions\n\n- **`structure.opening_gap`** -- already documented.\n",
        encoding="utf-8",
    )

    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 1
    # Nothing else should have been written for a refused scaffold.
    assert not (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "opening_gap.py"
    ).exists()


def test_scaffold_new_pack_creates_init_and_builtins_block(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "session.overlap_window",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0

    session_init = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "session"
        / "__init__.py"
    )
    assert session_init.is_file()
    init_source = session_init.read_text(encoding="utf-8")
    ast.parse(init_source)
    assert "OverlapWindowComponent" in init_source

    builtins_source = (
        tmp_path / "src" / "trading_framework" / "market_analysis" / "registry" / "builtins.py"
    ).read_text(encoding="utf-8")
    ast.parse(builtins_source)
    assert "from trading_framework.market_analysis.components.session import (" in builtins_source
    assert "register_overlap_window_component(registry)" in builtins_source
    # The pre-existing structure import block must survive untouched.
    assert "from trading_framework.market_analysis.components.structure import (" in (
        builtins_source
    )


def test_scaffold_generated_registry_files_stay_under_line_length_limit(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    for relative in (
        ("src", "trading_framework", "market_analysis", "components", "structure", "__init__.py"),
        ("src", "trading_framework", "market_analysis", "registry", "builtins.py"),
    ):
        source = tmp_path.joinpath(*relative).read_text(encoding="utf-8")
        assert all(len(line) <= 100 for line in source.splitlines())


def test_scaffold_refuses_when_class_names_already_present(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    first = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert first == 0

    # Delete the component/test files but leave the registration files patched,
    # simulating a corrupted half-state -- the tool must refuse, not double-patch.
    (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "opening_gap.py"
    ).unlink()
    (tmp_path / "tests" / "unit" / "market_analysis" / "test_opening_gap.py").unlink()

    second = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert second == 1


def test_scaffold_multi_word_name_uses_pascal_case(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.range_based_variance",
            "--repo-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    component_file = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "range_based_variance.py"
    )
    source = component_file.read_text(encoding="utf-8")
    assert "class RangeBasedVarianceComponent:" in source
    assert "class NumpyRangeBasedVarianceImplementation:" in source


def test_scaffold_refuses_to_overwrite_existing_component_file(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    first = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert first == 0

    second = scaffold_component.main(
        [
            "--component-id",
            "structure.opening_gap",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert second == 1


def test_scaffold_rejects_malformed_component_id(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        scaffold_component.main(
            [
                "--component-id",
                "NotDotted",
                "--repo-root",
                str(tmp_path),
            ]
        )


def test_scaffold_rejects_pack_mismatch(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        scaffold_component.main(
            [
                "--component-id",
                "structure.opening_gap",
                "--pack",
                "volatility",
                "--repo-root",
                str(tmp_path),
            ]
        )


def test_scaffold_refuses_no_causal_for_session_pack(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        scaffold_component.main(
            [
                "--component-id",
                "session.overlap_window",
                "--no-causal",
                "--repo-root",
                str(tmp_path),
            ]
        )


def test_scaffold_allows_no_causal_for_non_session_pack(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.delayed_thing",
            "--no-causal",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    component_file = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "delayed_thing.py"
    )
    assert "Causality.DELAYED" in component_file.read_text(encoding="utf-8")


def test_scaffold_records_depends_on_as_todo_comment(tmp_path: Path) -> None:
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.distance_to_level",
            "--depends-on",
            "structure.matched_extreme_pair",
            "--depends-on",
            "session.previous_period_extreme",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    component_file = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "distance_to_level.py"
    )
    source = component_file.read_text(encoding="utf-8")
    assert "structure.matched_extreme_pair" in source
    assert "session.previous_period_extreme" in source
    assert all(len(line) <= 100 for line in source.splitlines())


def test_scaffold_output_stays_ruff_line_length_clean_with_depends_on(
    tmp_path: Path,
) -> None:
    """Regression: a real multi-dependency case (Sprint N+2's
    structure.distance_to_level) must not push the generated TODO comment
    past the project's 100-char line-length gate."""
    _seed_registry(tmp_path)
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "structure.distance_to_level",
            "--depends-on",
            "structure.matched_extreme_pair",
            "--depends-on",
            "session.previous_period_extreme",
            "--repo-root",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    component_file = (
        tmp_path
        / "src"
        / "trading_framework"
        / "market_analysis"
        / "components"
        / "structure"
        / "distance_to_level.py"
    )
    source = component_file.read_text(encoding="utf-8")
    assert all(len(line) <= 100 for line in source.splitlines())
