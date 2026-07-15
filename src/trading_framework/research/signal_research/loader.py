"""Load Signal Research definitions from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.signal_research.definition import (
    SignalResearchDefinitionSpec,
)


class SignalResearchDefinitionLoadError(ValidationError):
    """Raised when a definition file cannot be parsed."""


def load_signal_research_definition_from_dict(
    payload: dict[str, Any],
) -> SignalResearchDefinitionSpec:
    """Parse a definition mapping into a validated spec."""
    return SignalResearchDefinitionSpec.from_dict(payload)


def load_signal_research_definition(path: Path | str) -> SignalResearchDefinitionSpec:
    """Load a definition from a ``.yaml``, ``.yml`` or ``.json`` file."""
    file_path = Path(path)
    if not file_path.is_file():
        msg = f"definition file not found: {file_path}"
        raise SignalResearchDefinitionLoadError(msg)

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml(text, source_path=file_path)
    else:
        msg = f"unsupported definition file extension: {suffix!r}"
        raise SignalResearchDefinitionLoadError(msg)

    if not isinstance(payload, dict):
        msg = "definition root must be a mapping"
        raise SignalResearchDefinitionLoadError(msg)
    return load_signal_research_definition_from_dict(payload)


def _load_yaml(text: str, *, source_path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = (
            "PyYAML is required to load YAML definitions; "
            f"install pyyaml or use JSON for {source_path}"
        )
        raise SignalResearchDefinitionLoadError(msg) from exc

    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        msg = f"YAML definition must deserialize to a mapping: {source_path}"
        raise SignalResearchDefinitionLoadError(msg)
    return loaded
