"""Architecture boundary tests for the Execution domain."""

import ast
from pathlib import Path

import trading_framework.execution as execution_package


def test_execution_domain_does_not_import_research_infrastructure_or_user_data() -> None:
    package_root = Path(execution_package.__file__).resolve().parent
    forbidden_prefixes = (
        "trading_framework.research",
        "trading_framework.infrastructure",
        "user_data",
    )
    offenders: list[str] = []

    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(package_root)}:{alias.name}"
                    for alias in node.names
                    if alias.name in forbidden_prefixes
                    or any(alias.name.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (
                    node.module in forbidden_prefixes
                    or any(node.module.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
                )
            ):
                offenders.append(f"{path.relative_to(package_root)}:{node.module}")

    assert offenders == []
