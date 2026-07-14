"""Consumer boundary tests for continuous futures preprocessing."""

from __future__ import annotations

import ast
from pathlib import Path

import trading_framework

_FORBIDDEN_IMPORT_PREFIXES = (
    "trading_framework.application.market_data.build_continuous",
    "trading_framework.application.market_data.build_roll_schedule",
    "trading_framework.application.market_data.materialize_continuous_trades",
    "trading_framework.application.market_data.derive_continuous_ohlcv",
    "trading_framework.application.market_data.import_databento_contract_trades_archive",
    "trading_framework.application.market_data.import_databento_trades_archive",
)

_CONSUMER_PACKAGE_SUFFIXES = (
    "application/strategy_research",
    "research",
)


def _python_files(package_root: Path, relative_suffix: str) -> list[Path]:
    target = package_root / relative_suffix
    if not target.exists():
        return []
    return [path for path in target.rglob("*.py") if path.is_file()]


def _collect_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return imports


def test_research_consumers_do_not_import_continuous_preprocessing() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent
    offenders: list[str] = []

    for suffix in _CONSUMER_PACKAGE_SUFFIXES:
        for path in _python_files(package_root, suffix):
            for imported in _collect_imports(path):
                if any(
                    imported == prefix or imported.startswith(f"{prefix}.")
                    for prefix in _FORBIDDEN_IMPORT_PREFIXES
                ):
                    offenders.append(f"{path.relative_to(package_root)}:{imported}")

    assert offenders == []
