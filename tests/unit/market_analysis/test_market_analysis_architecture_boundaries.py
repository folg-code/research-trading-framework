"""Market Analysis architecture boundary tests."""

import ast
from pathlib import Path

import trading_framework.market_analysis as market_analysis_package


def _python_files(package_root: Path) -> list[Path]:
    return [path for path in package_root.rglob("*.py") if path.is_file()]


def test_market_analysis_does_not_import_infrastructure_storage() -> None:
    package_root = Path(market_analysis_package.__file__).resolve().parent
    forbidden_prefixes = (
        "trading_framework.infrastructure",
        "trading_framework.application",
    )
    offenders: list[str] = []

    for path in _python_files(package_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    alias.name for alias in node.names if alias.name.startswith(forbidden_prefixes)
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.startswith(forbidden_prefixes)
            ):
                offenders.append(node.module)

    assert offenders == []
