"""Architecture boundary tests."""

import ast
from pathlib import Path

import trading_framework


def _python_files(package_root: Path) -> list[Path]:
    return [path for path in package_root.rglob("*.py") if path.is_file()]


def test_framework_does_not_import_user_data() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent
    offenders: list[str] = []

    for path in _python_files(package_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    alias.name
                    for alias in node.names
                    if alias.name == "user_data" or alias.name.startswith("user_data.")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (node.module == "user_data" or node.module.startswith("user_data."))
            ):
                offenders.append(node.module)

    assert offenders == []
