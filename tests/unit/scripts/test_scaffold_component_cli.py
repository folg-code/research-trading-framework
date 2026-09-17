"""CLI tests for scripts/market_analysis/scaffold_component.py (Sprint 065 T001)."""

import ast
from pathlib import Path

import pytest
from scripts.market_analysis import scaffold_component


def test_scaffold_writes_component_and_test_files(tmp_path: Path) -> None:
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


def test_scaffold_multi_word_name_uses_pascal_case(tmp_path: Path) -> None:
    exit_code = scaffold_component.main(
        [
            "--component-id",
            "volatility.range_based_variance",
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
        / "volatility"
        / "range_based_variance.py"
    )
    source = component_file.read_text(encoding="utf-8")
    assert "class RangeBasedVarianceComponent:" in source
    assert "class NumpyRangeBasedVarianceImplementation:" in source


def test_scaffold_refuses_to_overwrite_existing_component_file(tmp_path: Path) -> None:
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
