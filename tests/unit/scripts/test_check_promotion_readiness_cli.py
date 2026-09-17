"""CLI tests for scripts/market_analysis/check_promotion_readiness.py (Sprint 065 T004)."""

from pathlib import Path

from scripts.market_analysis import check_promotion_readiness as report

from trading_framework.market_analysis.identity.component import (
    ComponentId,
    ComponentVersion,
)
from trading_framework.market_analysis.models.dependencies import (
    ComponentDependency,
    DataFieldDependency,
)
from trading_framework.market_analysis.models.history import HistoryRequirement
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.outputs import (
    OutputFieldSpec,
    OutputId,
    OutputSchema,
)
from trading_framework.market_analysis.models.parameters import (
    CanonicalParameters,
    ParameterSchema,
)
from trading_framework.market_analysis.registry.builtins import default_mvp_registry

_REPO_ROOT = Path(__file__).resolve().parents[3]


class _FakeComponent:
    """Fake component for testing check_* functions in isolation, without
    going through the real (import-based) registry -- no session.* component
    exists in the registry yet to exercise the causal-only gate against."""

    __doc__ = "A plain, ordinary component."
    component_id = ComponentId("test.fake")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(fields=())
    output_schema = OutputSchema(outputs=(OutputFieldSpec(OutputId("value"), "float64"),))

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        return HistoryRequirement(bars_before=0)

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        return ()

    def component_dependencies(
        self, parameters: CanonicalParameters
    ) -> tuple[ComponentDependency, ...]:
        return ()


class _FakeUnfinishedComponent(_FakeComponent):
    __doc__ = "A freshly scaffolded, unfinished component."
    output_schema = OutputSchema(outputs=())

    def data_dependencies(self, parameters: CanonicalParameters) -> tuple[DataFieldDependency, ...]:
        raise NotImplementedError("TODO")

    def component_dependencies(
        self, parameters: CanonicalParameters
    ) -> tuple[ComponentDependency, ...]:
        raise NotImplementedError("TODO")


class _FakeSessionComponentWithSuspiciousDocstring(_FakeComponent):
    __doc__ = "Reports the full period high for the current session."


class _FakeNonCausalComponent(_FakeComponent):
    causality = Causality.DELAYED


# --- Individual check functions, tested directly against fakes ---


def test_check_output_schema_fails_on_empty_schema() -> None:
    result = report.check_output_schema(_FakeUnfinishedComponent())
    assert result.verdict is report.Verdict.FAIL


def test_check_output_schema_passes_with_at_least_one_field() -> None:
    result = report.check_output_schema(_FakeComponent())
    assert result.verdict is report.Verdict.PASS


def test_check_dependencies_declared_fails_on_not_implemented() -> None:
    result = report.check_dependencies_declared(_FakeUnfinishedComponent())
    assert result.verdict is report.Verdict.FAIL


def test_check_dependencies_declared_passes_when_implemented() -> None:
    result = report.check_dependencies_declared(_FakeComponent())
    assert result.verdict is report.Verdict.PASS


def test_check_causal_only_gate_not_applicable_for_non_session_pack() -> None:
    result = report.check_causal_only_gate("structure.opening_gap", _FakeComponent())
    assert result.verdict is report.Verdict.NOT_APPLICABLE


def test_check_causal_only_gate_fails_when_not_causal() -> None:
    result = report.check_causal_only_gate("session.overlap_window", _FakeNonCausalComponent())
    assert result.verdict is report.Verdict.FAIL


def test_check_causal_only_gate_flags_suspicious_language_for_review() -> None:
    result = report.check_causal_only_gate(
        "session.previous_period_extreme", _FakeSessionComponentWithSuspiciousDocstring()
    )
    assert result.verdict is report.Verdict.NEEDS_REVIEW
    assert "full period" in result.detail


def test_check_causal_only_gate_passes_for_clean_session_component() -> None:
    result = report.check_causal_only_gate("session.overlap_window", _FakeComponent())
    assert result.verdict is report.Verdict.PASS


# --- Registered/tested/catalog checks, against the real repo and real registry ---


def test_check_registered_passes_for_a_real_component() -> None:
    registry = default_mvp_registry()
    result, component = report.check_registered("structure.level_distance", registry)
    assert result.verdict is report.Verdict.PASS
    assert component is not None


def test_check_registered_fails_for_an_unknown_component() -> None:
    registry = default_mvp_registry()
    result, component = report.check_registered("structure.does_not_exist", registry)
    assert result.verdict is report.Verdict.FAIL
    assert component is None


def test_check_registered_fails_gracefully_for_a_malformed_id() -> None:
    registry = default_mvp_registry()
    result, component = report.check_registered("not-dotted", registry)
    assert result.verdict is report.Verdict.FAIL
    assert component is None


def test_check_tested_and_catalog_entry_pass_for_a_real_documented_component() -> None:
    tested = report.check_tested(_REPO_ROOT, "structure.level_distance")
    assert tested.verdict is report.Verdict.PASS
    catalog = report.check_catalog_entry(_REPO_ROOT, "structure.level_distance")
    assert catalog.verdict is report.Verdict.PASS


def test_check_tested_fails_when_no_test_file_exists(tmp_path: Path) -> None:
    result = report.check_tested(tmp_path, "structure.opening_gap")
    assert result.verdict is report.Verdict.FAIL


def test_check_catalog_entry_fails_when_marked_with_todo(tmp_path: Path) -> None:
    catalog_file = tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    catalog_file.write_text(
        "- **`structure.opening_gap`** -- <!-- TODO: fill in before promotion -->\n",
        encoding="utf-8",
    )
    result = report.check_catalog_entry(tmp_path, "structure.opening_gap")
    assert result.verdict is report.Verdict.FAIL
    assert "TODO" in result.detail


def test_check_catalog_entry_fails_when_missing(tmp_path: Path) -> None:
    catalog_file = tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    catalog_file.write_text("nothing relevant here\n", encoding="utf-8")
    result = report.check_catalog_entry(tmp_path, "structure.opening_gap")
    assert result.verdict is report.Verdict.FAIL


# --- run_checks / main() end-to-end ---


def test_run_checks_all_pass_for_real_fully_documented_component() -> None:
    registry = default_mvp_registry()
    results = report.run_checks("structure.level_distance", _REPO_ROOT, registry)
    by_name = {result.name: result for result in results}
    assert by_name["registered"].verdict is report.Verdict.PASS
    assert by_name["tested"].verdict is report.Verdict.PASS
    assert by_name["catalog_entry"].verdict is report.Verdict.PASS
    assert by_name["output_schema"].verdict is report.Verdict.PASS
    assert by_name["dependencies_declared"].verdict is report.Verdict.PASS
    assert by_name["causal_only_gate"].verdict is report.Verdict.NOT_APPLICABLE


def test_run_checks_reports_not_applicable_when_unregistered(tmp_path: Path) -> None:
    registry = default_mvp_registry()
    results = report.run_checks("structure.does_not_exist", tmp_path, registry)
    by_name = {result.name: result for result in results}
    assert by_name["registered"].verdict is report.Verdict.FAIL
    assert by_name["output_schema"].verdict is report.Verdict.NOT_APPLICABLE
    assert by_name["dependencies_declared"].verdict is report.Verdict.NOT_APPLICABLE
    assert by_name["causal_only_gate"].verdict is report.Verdict.NOT_APPLICABLE


def test_main_exits_zero_when_everything_passes_or_is_not_applicable() -> None:
    exit_code = report.main(
        ["--component-id", "structure.level_distance", "--repo-root", str(_REPO_ROOT)]
    )
    assert exit_code == 0


def test_main_exits_nonzero_on_a_real_failure(tmp_path: Path) -> None:
    exit_code = report.main(
        ["--component-id", "structure.does_not_exist", "--repo-root", str(tmp_path)]
    )
    assert exit_code == 1


def test_main_reports_gracefully_on_a_malformed_component_id(tmp_path: Path) -> None:
    """A malformed --component-id (no dot) must report FAIL, not crash."""
    exit_code = report.main(["--component-id", "not-dotted", "--repo-root", str(tmp_path)])
    assert exit_code == 1


def test_main_never_writes_to_the_real_component_or_catalog_files(tmp_path: Path) -> None:
    catalog_file = tmp_path / "docs" / "reference" / "modules" / "ANALYSIS_COMPONENT_CATALOG.md"
    catalog_file.parent.mkdir(parents=True, exist_ok=True)
    catalog_file.write_text("original content\n", encoding="utf-8")
    before = catalog_file.stat().st_mtime_ns

    report.main(["--component-id", "structure.level_distance", "--repo-root", str(tmp_path)])

    assert catalog_file.stat().st_mtime_ns == before
    assert catalog_file.read_text(encoding="utf-8") == "original content\n"


def test_main_writes_markdown_report_when_requested(tmp_path: Path) -> None:
    out_file = tmp_path / "report.md"
    exit_code = report.main(
        [
            "--component-id",
            "structure.level_distance",
            "--repo-root",
            str(_REPO_ROOT),
            "--markdown-out",
            str(out_file),
        ]
    )
    assert exit_code == 0
    assert out_file.is_file()
    markdown = out_file.read_text(encoding="utf-8")
    assert "| Component | Check | Verdict | Detail |" in markdown
    assert "structure.level_distance" in markdown
