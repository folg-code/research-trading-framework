"""Architecture boundary tests for apps/* consumers (ADR-0022 / D-S029-03).

`apps/dashboard` and `apps/cli` have *different* import boundaries (ADR-0026
§2, D-S046-06): the dashboard reads persisted artifacts and may not import
`trading_framework` at all, while the CLI invokes workflows and may import
`trading_framework.application.*`, plus a short, explicit allow-list of
non-application leaf modules Wave 2 found genuinely necessary (typed
identifiers, value objects, and the two hardcoded defaults documented in
SPRINT_046.md §4 finding 2 -- see the allow-list below for the per-module
reason). Each app therefore gets its own scoped test below rather than one
rule applied uniformly over `apps/*`.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI_ALLOWLIST_TEST_FILE = Path(__file__).resolve()
_APPS_ROOT = _REPO_ROOT / "apps"
_DASHBOARD_SRC = _APPS_ROOT / "dashboard" / "src"

_FORBIDDEN_PREFIXES = (
    "trading_framework.research",
    "trading_framework.application.strategy_research",
    "trading_framework.application.robustness_research",
    "trading_framework.application.predictive_research",
    "trading_framework.execution",
    "trading_framework.infrastructure.providers",
    "trading_framework.infrastructure.importers",
)

# ADR-0022 / Sprint 044 §4: the dashboard environment must never install a
# research-only ML library. These are third-party training/estimator
# libraries, not part of trading_framework itself.
_FORBIDDEN_ML_LIBRARY_PREFIXES = (
    "sklearn",
    "xgboost",
    "torch",
)


def _python_files(package_root: Path) -> list[Path]:
    return [path for path in package_root.rglob("*.py") if path.is_file()]


def _is_forbidden(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes)


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.append(node.module)
    return modules


def test_dashboard_does_not_import_forbidden_framework_packages() -> None:
    assert _DASHBOARD_SRC.is_dir(), "expected apps/dashboard/src (ADR-0022)"
    offenders: list[str] = []

    for path in _python_files(_DASHBOARD_SRC):
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for module in _imported_modules(path):
            if _is_forbidden(module, _FORBIDDEN_PREFIXES):
                offenders.append(f"{relative}:{module}")

    assert offenders == []


def test_dashboard_does_not_import_ml_training_libraries() -> None:
    """apps/dashboard must not depend on research-only ML libraries (ADR-0022 §4, S044).

    The dashboard reads persisted facts (parquet/json); it never trains or
    scores a model itself, so scikit-learn, XGBoost and torch have no reason
    to appear in any dashboard source file.
    """
    assert _DASHBOARD_SRC.is_dir(), "expected apps/dashboard/src (ADR-0022)"
    offenders: list[str] = []

    for path in _python_files(_DASHBOARD_SRC):
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for module in _imported_modules(path):
            if _is_forbidden(module, _FORBIDDEN_ML_LIBRARY_PREFIXES):
                offenders.append(f"{relative}:{module}")

    assert offenders == []


# ---------------------------------------------------------------------------
# apps/cli -- a deliberately different, relaxed-but-still-enforced boundary
# (ADR-0026 §2, D-S046-06, S046-T004). The CLI invokes application-layer
# workflows, so it MAY import `trading_framework.application.*`, but must
# never reach past that layer into research/market_analysis/strategy/
# execution logic or an infrastructure adapter directly.
#
# Wave 2 (S046-T005..T009) found that a strict `application.*`-only allow-list
# is narrower than an operator-facing CLI can honour: several application
# Request dataclasses take domain *value objects* and *typed identifiers* as
# constructor arguments (e.g. `EstimatorSpec`, `PredictiveDatasetRef`,
# `DatasetRef`, `TimeRange`, `Timeframe`), and Sprint 046 §4 finding 2 locks
# two research-layer defaults (`SimulationAssumptions()`,
# `build_canonical_strategy_model()`, `CmeEsRthSessionResolver()`) as
# hardcoded, inherited limitations rather than something the CLI recomputes.
# Each entry below is one specific leaf module, added because a Wave 2 command
# genuinely needs it to construct a request or reference a typed identifier --
# never a blanket `research.*`/`strategy.*` allowance, and never research,
# simulation or execution *logic* implemented inside apps/cli. See
# apps/cli/CLAUDE.md and the Wave 2 integration PR description for the
# per-module justification.
# ---------------------------------------------------------------------------

_CLI_SRC = _APPS_ROOT / "cli" / "src"
_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX = "trading_framework.application"
_CLI_ALLOWED_TRADING_FRAMEWORK_MODULES = frozenset(
    {
        # exception type used in `except` clauses around application calls
        "trading_framework.core.exceptions",
        # value object: framework identifier wrapper
        "trading_framework.core.identifiers",
        # read-only dataset metadata lookup mirroring the wrapped script
        # (run_strategy_research.py); no other infrastructure adapter is used
        "trading_framework.infrastructure.storage.metadata.registry",
        # typed identifiers/value objects (DatasetRef, DatasetId)
        "trading_framework.market.datasets",
        # config value object for the Databento archive import workflow
        "trading_framework.market.importers",
        # value object required by RunStrategyResearchRequest
        "trading_framework.market_analysis.models.time_range",
        # existing HTML renderer, called (never reimplemented) for
        # `report render strategy` -- application only builds the view model
        "trading_framework.research.analytics.strategy_dashboard_report",
        # typed identifiers produced/consumed between composed steps
        # (build -> run -> render), never round-tripped through stdout
        "trading_framework.research.datasets.predictive",
        "trading_framework.research.datasets.predictive_run",
        "trading_framework.research.datasets.strategy_research",
        # spec error type raised by the estimator/study loaders below
        "trading_framework.research.predictive.errors",
        # `EstimatorSpec.from_dict` is the spec's own validating loader
        # (D-S046-07: referenced by path, never re-encoded)
        "trading_framework.research.predictive.estimators",
        # `load_predictive_study_spec` is PredictiveStudySpec's own loader
        "trading_framework.research.predictive.spec",
        # SPRINT_046.md §4 finding 2: hardcoded default, same as the script
        "trading_framework.research.simulation",
        # SPRINT_046.md §4 finding 2: hardcoded canonical strategy model
        "trading_framework.strategy",
        # value object required by several application Requests
        "trading_framework.time.models.timeframe",
        # SPRINT_046.md §4 finding 2: hardcoded session resolver
        "trading_framework.time.sessions",
    }
)


def _is_cli_boundary_violation(module_name: str) -> bool:
    if module_name == "trading_framework":
        return True
    if not module_name.startswith("trading_framework."):
        return False
    if module_name == _CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX or module_name.startswith(
        f"{_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX}."
    ):
        return False
    return not any(
        module_name == allowed or module_name.startswith(f"{allowed}.")
        for allowed in _CLI_ALLOWED_TRADING_FRAMEWORK_MODULES
    )


def test_cli_only_imports_application_layer() -> None:
    assert _CLI_SRC.is_dir(), "expected apps/cli/src (ADR-0026)"
    offenders: list[str] = []

    for path in _python_files(_CLI_SRC):
        relative = path.relative_to(_REPO_ROOT).as_posix()
        for module in _imported_modules(path):
            if _is_cli_boundary_violation(module):
                offenders.append(f"{relative}:{module}")

    assert offenders == []


# ---------------------------------------------------------------------------
# Sprint 047 / S047-T004: the loader (trading_cli/strategy_loader.py) needs
# `trading_framework.strategy`, which was already on the allow-list (Amendment
# 1, added for `build_canonical_strategy_model`). SPRINT_047.md §4 finding 2
# claims this requires *zero* widening -- this test asserts that claim rather
# than assuming it: the allow-list constant below is byte-identical to what
# `git show origin/main:...` returns for this same file. If a future PR needs
# to widen the allow-list, that is a new ADR-0026 amendment with fresh
# maintainer approval (D-S047-08) -- never a silent edit here.
# ---------------------------------------------------------------------------


def _git_show_main_file(relative_posix_path: str) -> str | None:
    """Return this file's content on `origin/main`, or None if unavailable.

    None (never a failure) when the ref can't be resolved -- e.g. a shallow
    clone with no `origin/main` -- so this assertion degrades to a skip
    rather than a false failure on an unrelated CI/checkout shape.
    """
    for ref in ("origin/main", "main"):
        try:
            result = subprocess.run(  # fixed args, read-only "git show"
                ["git", "show", f"{ref}:{relative_posix_path}"],
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0 and result.stdout:
            return result.stdout
    return None


def test_cli_boundary_allow_list_is_byte_identical_to_main() -> None:
    """SPRINT_047.md §4 finding 2 / D-S047-08: the loader widens nothing."""
    relative_path = _CLI_ALLOWLIST_TEST_FILE.relative_to(_REPO_ROOT).as_posix()
    main_content = _git_show_main_file(relative_path)
    if main_content is None:
        pytest.skip("origin/main not reachable in this checkout; cannot diff against it")

    current_content = _CLI_ALLOWLIST_TEST_FILE.read_text(encoding="utf-8")

    current_block = _extract_allow_list_block(current_content)
    main_block = _extract_allow_list_block(main_content)

    assert current_block == main_block, (
        "apps/cli's import allow-list changed relative to main -- widening it "
        "requires a new ADR-0026 amendment with fresh maintainer approval "
        "(D-S047-08), not an edit to this test"
    )


_ALLOW_LIST_START_MARKER = "_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX = "
_ALLOW_LIST_END_MARKER = "\n)\n"


def _extract_allow_list_block(source: str) -> str:
    """Return the exact `_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX`/`_MODULES` text.

    Extracting just this block (rather than diffing the whole file) keeps the
    assertion scoped to what Finding 2 actually claims -- the allow-list
    itself -- and immune to unrelated docstring/comment edits elsewhere in
    the file.
    """
    start = source.index(_ALLOW_LIST_START_MARKER)
    end = source.index(_ALLOW_LIST_END_MARKER, start) + len(_ALLOW_LIST_END_MARKER)
    return source[start:end]
