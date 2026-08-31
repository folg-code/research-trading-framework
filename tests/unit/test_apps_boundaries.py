"""Architecture boundary tests for apps/* consumers (ADR-0022 / D-S029-03).

`apps/dashboard` and `apps/cli` have *different* import boundaries (ADR-0026
§2, D-S046-06): the dashboard reads persisted artifacts and may not import
`trading_framework` at all, while the CLI invokes workflows and may import
`trading_framework.application.*` only. Each app therefore gets its own
scoped test below rather than one rule applied uniformly over `apps/*`.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
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
# ---------------------------------------------------------------------------

_CLI_SRC = _APPS_ROOT / "cli" / "src"
_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX = "trading_framework.application"


def _is_cli_boundary_violation(module_name: str) -> bool:
    if module_name == "trading_framework":
        return True
    if not module_name.startswith("trading_framework."):
        return False
    return not (
        module_name == _CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX
        or module_name.startswith(f"{_CLI_ALLOWED_TRADING_FRAMEWORK_PREFIX}.")
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
