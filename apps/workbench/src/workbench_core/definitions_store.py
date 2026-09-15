"""Saved Signal Research definition store (Sprint 064 T008).

`user_data/workbench/definitions/<name>.yaml` holds an operator's saved,
editable `SignalResearchDefinitionSpec` payload -- the exact same shape a
template's `apply` response or a hand-authored definition file already uses
(ADR-0038 section 1: never a second schema). This is workbench-owned
convenience state, the same category as `jobs/` (ADR-0041 section 3):
deleting the whole `definitions/` tree loses no research artifact, only the
operator's saved drafts. A job's `definition_path` (T006) can point directly
at one of these files -- the same path an operator would hand to
`trading-cli` directly, satisfying T008's "the saved YAML runs unchanged
through T002 from a terminal" acceptance criterion.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_DEFINITIONS_DIR_NAME = "definitions"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$")


class InvalidDefinitionNameError(ValueError):
    """Raised when a definition `name` is empty, too long, or contains a
    character that would let it escape `definitions/` (path traversal) or
    collide across platforms."""


class DefinitionNotFoundError(LookupError):
    """Raised when no saved definition matches `name`."""


def definitions_root(storage_root: Path) -> Path:
    return storage_root / "workbench" / _DEFINITIONS_DIR_NAME


def definition_path(storage_root: Path, name: str) -> Path:
    _require_safe_name(name)
    return definitions_root(storage_root) / f"{name}.yaml"


def save_definition(storage_root: Path, name: str, definition: dict[str, object]) -> Path:
    """Write `definition` to `definitions/<name>.yaml`, overwriting any
    existing save with that name (an explicit re-save, not a version)."""
    path = definition_path(storage_root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(definition, sort_keys=False), encoding="utf-8")
    return path


def load_definition(storage_root: Path, name: str) -> dict[str, object]:
    path = definition_path(storage_root, name)
    if not path.is_file():
        msg = f"no saved definition named {name!r}"
        raise DefinitionNotFoundError(msg)
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        msg = f"saved definition {name!r} is corrupt: root is not a mapping"
        raise DefinitionNotFoundError(msg)
    return loaded


def list_definition_names(storage_root: Path) -> tuple[str, ...]:
    root = definitions_root(storage_root)
    if not root.is_dir():
        return ()
    return tuple(sorted(path.stem for path in root.glob("*.yaml")))


def _require_safe_name(name: str) -> None:
    if not _SAFE_NAME.match(name):
        msg = (
            f"invalid definition name {name!r}: must be 1-100 characters, "
            "starting with a letter or digit, using only letters, digits, '_' and '-'"
        )
        raise InvalidDefinitionNameError(msg)
