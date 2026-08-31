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


def _wave4_predictive_paths() -> tuple[Path, ...]:
    framework_root = Path(trading_framework.__file__).resolve().parent
    repo_root = framework_root.parents[1]
    return (
        framework_root / "research" / "datasets" / "predictive.py",
        framework_root / "research" / "datasets" / "predictive_run.py",
        framework_root / "research" / "reporting" / "predictive",
        framework_root / "application" / "predictive_research",
        repo_root / "scripts" / "predictive_research",
    )


def _import_offenders_from_roots(
    roots: tuple[Path, ...],
    *,
    predicate: Callable[[str], bool],
) -> list[str]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        else:
            files.extend(_python_files(root))
    offenders: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.name}:{alias.name}" for alias in node.names if predicate(alias.name)
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and predicate(node.module)
            ):
                offenders.append(f"{path.name}:{node.module}")
    return offenders


_SIGNING_MODULE_NAMES = frozenset({"hmac"})
#: Only the literal header Binance uses to carry a request signature -- unlike
#: the words "hmac"/"signature", this string cannot appear in ordinary prose
#: (docstrings/comments referencing ADR-0025 legitimately say "no signature").
_SIGNED_ENDPOINT_HEADER = "x-mbx-signature"


def _is_signing_module(dotted_name: str) -> bool:
    lowered = dotted_name.lower()
    return lowered in _SIGNING_MODULE_NAMES or lowered.startswith("hmac.")


def test_binance_provider_has_no_signing_code_or_authenticated_endpoint() -> None:
    """ADR-0025 §5: no HMAC/signature usage anywhere in the Binance provider package.

    This is the structural guarantee behind D-S045-08: the optional API key can
    only ever reach a public market-data GET, because no code path exists that
    could compute a request signature for an authenticated endpoint.
    """
    package_root = Path(trading_framework.__file__).resolve().parent
    binance_root = package_root / "infrastructure" / "providers" / "binance"
    offenders: list[str] = []

    for path in _python_files(binance_root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(package_root)}:import {alias.name}"
                    for alias in node.names
                    if _is_signing_module(alias.name)
                )
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                if _is_signing_module(node.module):
                    offenders.append(f"{path.relative_to(package_root)}:from {node.module}")
            elif isinstance(node, ast.Name) and node.id.lower() in _SIGNING_MODULE_NAMES:
                offenders.append(f"{path.relative_to(package_root)}:name {node.id}")
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.lower() == _SIGNED_ENDPOINT_HEADER
            ):
                offenders.append(f"{path.relative_to(package_root)}:header {node.value!r}")

    assert offenders == []


def test_no_urllib_import_outside_infrastructure() -> None:
    """HTTP access (urllib) is confined to ``infrastructure/`` (SPRINT_045.md §4).

    Application, research and script layers must never see ``urllib`` or raw
    HTTP directly -- they call an application workflow that already returns
    domain objects.
    """
    package_root = Path(trading_framework.__file__).resolve().parent
    infrastructure_root = package_root / "infrastructure"
    offenders: list[str] = []

    for path in _python_files(package_root):
        if infrastructure_root in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f"{path.relative_to(package_root)}:{alias.name}"
                    for alias in node.names
                    if alias.name == "urllib" or alias.name.startswith("urllib.")
                )
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (node.module == "urllib" or node.module.startswith("urllib."))
            ):
                offenders.append(f"{path.relative_to(package_root)}:{node.module}")

    assert offenders == []


def test_predictive_research_does_not_import_ml_libraries() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"

    assert _import_offenders(package_root, predicate=_is_ml_library) == []


def test_predictive_research_does_not_import_ml_infrastructure() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"

    def is_ml_infrastructure(module_name: str) -> bool:
        return module_name == "trading_framework.infrastructure.ml" or module_name.startswith(
            "trading_framework.infrastructure.ml."
        )

    assert _import_offenders(package_root, predicate=is_ml_infrastructure) == []


def test_domain_modules_do_not_import_ml_libraries() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent
    ml_adapters = package_root / "infrastructure" / "ml"

    assert (
        _import_offenders(package_root, predicate=_is_ml_library, skip_roots=(ml_adapters,)) == []
    )


def test_predictive_research_does_not_import_trading_capabilities() -> None:
    package_root = Path(trading_framework.__file__).resolve().parent / "research" / "predictive"

    assert _import_offenders(package_root, predicate=_is_forbidden_predictive_import) == []


def test_predictive_research_wave4_packages_do_not_import_ml_libraries() -> None:
    assert _import_offenders_from_roots(_wave4_predictive_paths(), predicate=_is_ml_library) == []


def test_predictive_report_package_does_not_import_ml_infrastructure() -> None:
    package_root = (
        Path(trading_framework.__file__).resolve().parent / "research" / "reporting" / "predictive"
    )

    def is_ml_infrastructure(module_name: str) -> bool:
        return module_name == "trading_framework.infrastructure.ml" or module_name.startswith(
            "trading_framework.infrastructure.ml."
        )

    assert _import_offenders(package_root, predicate=is_ml_infrastructure) == []


def test_predictive_research_wave4_packages_do_not_import_trading_capabilities() -> None:
    assert (
        _import_offenders_from_roots(
            _wave4_predictive_paths(),
            predicate=_is_forbidden_predictive_import,
        )
        == []
    )
