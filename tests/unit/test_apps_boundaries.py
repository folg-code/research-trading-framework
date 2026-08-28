"""Architecture boundary tests for apps/* consumers (ADR-0022 / D-S029-03)."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_APPS_ROOT = _REPO_ROOT / "apps"

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


def test_apps_do_not_import_forbidden_framework_packages() -> None:
    assert _APPS_ROOT.is_dir(), "expected apps/ top-level tier (ADR-0022)"
    offenders: list[str] = []

    for app_src in _APPS_ROOT.glob("*/src"):
        for path in _python_files(app_src):
            relative = path.relative_to(_REPO_ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden(alias.name, _FORBIDDEN_PREFIXES):
                            offenders.append(f"{relative}:{alias.name}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module is not None
                    and _is_forbidden(node.module, _FORBIDDEN_PREFIXES)
                ):
                    offenders.append(f"{relative}:{node.module}")

    assert offenders == []


def test_apps_do_not_import_ml_training_libraries() -> None:
    """apps/* must not depend on research-only ML libraries (ADR-0022 §4, S044).

    The dashboard reads persisted facts (parquet/json); it never trains or
    scores a model itself, so scikit-learn, XGBoost and torch have no reason
    to appear in any apps/* source file.
    """
    assert _APPS_ROOT.is_dir(), "expected apps/ top-level tier (ADR-0022)"
    offenders: list[str] = []

    for app_src in _APPS_ROOT.glob("*/src"):
        for path in _python_files(app_src):
            relative = path.relative_to(_REPO_ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden(alias.name, _FORBIDDEN_ML_LIBRARY_PREFIXES):
                            offenders.append(f"{relative}:{alias.name}")
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module is not None
                    and _is_forbidden(node.module, _FORBIDDEN_ML_LIBRARY_PREFIXES)
                ):
                    offenders.append(f"{relative}:{node.module}")

    assert offenders == []
