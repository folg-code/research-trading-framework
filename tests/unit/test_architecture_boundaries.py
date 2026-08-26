"""Architecture boundary tests."""

import ast
from collections.abc import Callable
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


def test_databento_imports_only_in_infrastructure() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent
    allowed_prefix = package_root / "infrastructure" / "importers" / "databento"
    offenders: list[str] = []

    for path in _python_files(package_root):
        if allowed_prefix in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(package_root)}:{alias.name}"
                    for alias in node.names
                    if alias.name == "databento" or alias.name.startswith("databento.")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (node.module == "databento" or node.module.startswith("databento."))
            ):
                offenders.append(f"{path.relative_to(package_root)}:{node.module}")

    assert offenders == []


_ML_LIBRARY_ROOTS = (
    "sklearn",
    "xgboost",
    "lightgbm",
    "catboost",
    "torch",
)

_PREDICTIVE_FORBIDDEN_PREFIXES = (
    "trading_framework.strategy",
    "trading_framework.signal_model",
    "trading_framework.research.simulation",
    "trading_framework.execution",
)


def _is_ml_library(module_name: str) -> bool:
    return module_name in _ML_LIBRARY_ROOTS or any(
        module_name.startswith(f"{root}.") for root in _ML_LIBRARY_ROOTS
    )


def _is_forbidden_predictive_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in _PREDICTIVE_FORBIDDEN_PREFIXES
    )


def _import_offenders(
    package_root: Path,
    *,
    predicate: Callable[[str], bool],
    skip_roots: tuple[Path, ...] = (),
) -> list[str]:
    offenders: list[str] = []
    for path in _python_files(package_root):
        if any(root in path.parents or path.parent == root for root in skip_roots):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(package_root)}:{alias.name}"
                    for alias in node.names
                    if predicate(alias.name)
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and predicate(node.module)
            ):
                offenders.append(f"{path.relative_to(package_root)}:{node.module}")
    return offenders


def test_predictive_research_does_not_import_ml_libraries() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"

    assert _import_offenders(package_root, predicate=_is_ml_library) == []


def test_domain_modules_do_not_import_ml_libraries() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent
    ml_adapters = package_root / "infrastructure" / "ml"

    assert (
        _import_offenders(package_root, predicate=_is_ml_library, skip_roots=(ml_adapters,)) == []
    )


def test_predictive_research_does_not_import_trading_capabilities() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"

    assert _import_offenders(package_root, predicate=_is_forbidden_predictive_import) == []
