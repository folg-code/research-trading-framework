"""Operator-authored strategy file loader (S047-T002, ADR-0027 mechanism).

Loads a `research.strategy.strategy_file` path as a Python module using
`importlib.util.spec_from_file_location`, resolves its conventional
zero-argument `build_strategy() -> StrategyModelDefinition` entry point, calls
it, and validates the result -- following ADR-0027 Sec3 exactly:

    spec = importlib.util.spec_from_file_location(synthetic_name, resolved_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[synthetic_name] = module        # BEFORE exec_module
    spec.loader.exec_module(module)
    entry = getattr(module, "build_strategy")
    definition = entry()

Trust model (ADR-0027 Sec2, D-S047-09): there is no sandbox, no import
restriction, no AST inspection, no subprocess isolation. Loading a strategy
file has the exact same blast radius as ``uv run python <that file>`` -- the
operator's own trusted code, running with the operator's own privileges.

Error taxonomy (ADR-0027 Sec5 / D-S047-07, nine rows, binding):

    path missing / not a file / a directory       -> ConfigError, exit 2
    extension is not '.py'                        -> ConfigError, exit 2
    the module raises during import                -> ConfigError, exit 2 (chained)
    no 'build_strategy' attribute                   -> ConfigError, exit 2
    'build_strategy' is not callable                -> ConfigError, exit 2
    'build_strategy' requires arguments              -> ConfigError, exit 2
    'build_strategy()' raises                        -> WorkflowError, exit 1 (chained)
    return value is not a StrategyModelDefinition    -> ConfigError, exit 2
    the definition fails validate_strategy_model_definition -> ConfigError, exit 2

Every chained error preserves ``__cause__`` (``raise ... from exc``) so
``--verbose`` shows the operator their own traceback -- nothing is swallowed.

Binding, locked mechanics (D-S047-06):

- ``sys.path`` is NEVER mutated. A strategy needing sibling imports is the
  operator's own packaging problem (the guide documents ``PYTHONPATH``).
- The synthetic module name is
  ``trading_cli._loaded_strategy.<sha256(resolved_path)[:12]>`` -- collision-
  proof for two different files sharing a stem -- and is registered in
  ``sys.modules`` before ``exec_module`` runs. It is an implementation detail;
  nothing may depend on its exact value.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from trading_framework.strategy import (
    StrategyModelDefinition,
    StrategyModelDefinitionError,
    validate_strategy_model_definition,
)

from trading_cli.errors import ConfigError, WorkflowError

_SYNTHETIC_MODULE_PREFIX = "trading_cli._loaded_strategy"
_ENTRY_POINT_NAME = "build_strategy"
_CONFIG_KEY = "research.strategy.strategy_file"


@dataclass(frozen=True, slots=True)
class LoadedStrategy:
    """The result of loading and validating an operator-authored strategy file."""

    strategy_file: Path
    definition: StrategyModelDefinition


def load_strategy_definition(strategy_file: str) -> LoadedStrategy:
    """Load, execute and validate the strategy file named by ``strategy_file``.

    ``strategy_file`` is resolved relative to the process working directory,
    then made absolute (D-S047-03). Every failure mode is a pre-flight
    ``ConfigError``/``WorkflowError`` as specified by ADR-0027 Sec5 -- this
    function performs no framework side effect of its own.
    """
    resolved_path = Path(strategy_file).resolve()
    _validate_path(resolved_path)
    module = _import_module(resolved_path)
    entry = _resolve_entry_point(module, resolved_path)
    raw_result = _call_entry_point(entry, resolved_path)
    definition = _validate_return_type(raw_result, resolved_path)
    _validate_definition(definition, resolved_path)
    return LoadedStrategy(strategy_file=resolved_path, definition=definition)


def _validate_path(resolved_path: Path) -> None:
    if not resolved_path.exists():
        raise ConfigError(f"'{_CONFIG_KEY}' not found: {resolved_path}")
    if resolved_path.is_dir():
        raise ConfigError(f"'{_CONFIG_KEY}' is a directory, not a file: {resolved_path}")
    if not resolved_path.is_file():
        raise ConfigError(f"'{_CONFIG_KEY}' is not a regular file: {resolved_path}")
    if resolved_path.suffix != ".py":
        raise ConfigError(
            f"'{_CONFIG_KEY}' must point at a '.py' file; got extension "
            f"{resolved_path.suffix!r}: {resolved_path}"
        )


def _synthetic_module_name(resolved_path: Path) -> str:
    digest = hashlib.sha256(str(resolved_path).encode("utf-8")).hexdigest()[:12]
    return f"{_SYNTHETIC_MODULE_PREFIX}.{digest}"


def _import_module(resolved_path: Path) -> ModuleType:
    synthetic_name = _synthetic_module_name(resolved_path)
    spec = importlib.util.spec_from_file_location(synthetic_name, resolved_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive, unreachable for .py
        raise ConfigError(
            f"'{_CONFIG_KEY}' could not be loaded as a Python module: {resolved_path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[synthetic_name] = module  # registered BEFORE exec_module (D-S047-06)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(synthetic_name, None)
        raise ConfigError(f"'{_CONFIG_KEY}' raised while importing {resolved_path}: {exc}") from exc
    return module


def _resolve_entry_point(module: ModuleType, resolved_path: Path) -> Callable[..., Any]:
    if not hasattr(module, _ENTRY_POINT_NAME):
        raise ConfigError(
            f"'{_CONFIG_KEY}' {resolved_path} must define a zero-argument "
            f"'{_ENTRY_POINT_NAME}()' function; no '{_ENTRY_POINT_NAME}' attribute was found"
        )
    entry = getattr(module, _ENTRY_POINT_NAME)
    if not callable(entry):
        raise ConfigError(
            f"'{_ENTRY_POINT_NAME}' in {resolved_path} must be callable; "
            f"got a {type(entry).__name__!r} value"
        )
    _require_zero_required_arguments(entry, resolved_path)
    return entry


def _require_zero_required_arguments(entry: Callable[..., Any], resolved_path: Path) -> None:
    try:
        signature = inspect.signature(entry)
    except (TypeError, ValueError):  # pragma: no cover - defensive, e.g. some C builtins
        return
    required = [
        name
        for name, param in signature.parameters.items()
        if param.default is inspect.Parameter.empty
        and param.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]
    if required:
        raise ConfigError(
            f"'{_ENTRY_POINT_NAME}' in {resolved_path} requires argument(s) "
            f"{', '.join(required)}; it must be callable with zero arguments"
        )


def _call_entry_point(entry: Callable[..., Any], resolved_path: Path) -> Any:
    try:
        return entry()
    except Exception as exc:
        raise WorkflowError(f"'{_ENTRY_POINT_NAME}()' in {resolved_path} raised: {exc}") from exc


def _validate_return_type(raw_result: Any, resolved_path: Path) -> StrategyModelDefinition:
    if not isinstance(raw_result, StrategyModelDefinition):
        raise ConfigError(
            f"'{_ENTRY_POINT_NAME}()' in {resolved_path} must return a "
            f"StrategyModelDefinition; got {type(raw_result).__name__!r}"
        )
    return raw_result


def _validate_definition(definition: StrategyModelDefinition, resolved_path: Path) -> None:
    try:
        validate_strategy_model_definition(definition)
    except StrategyModelDefinitionError as exc:
        raise ConfigError(
            f"the StrategyModelDefinition returned by {resolved_path} failed validation: {exc}"
        ) from exc
