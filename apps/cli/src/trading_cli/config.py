"""YAML config loader and strict validation (D-S046-07, D-S046-08).

Schema shape (locked): a thin common envelope (`version`, `storage_root`),
four optional per-command-group blocks (`data`, `research`, `dry_run`,
`report`), and pass-through references (by path) to existing spec files such
as `PredictiveStudySpec` / `EstimatorSpec` -- those files are never inlined
or re-parsed here.

Validation rules, all enforced before any side effect:

- `version` and `storage_root` are required; every other top-level key must
  be one of `data`, `research`, `dry_run`, `report`.
- unknown keys at any level are a hard error naming the offending key and,
  when reasonably cheap, the closest valid key.
- a key that looks credential-shaped (``api_key``, ``secret``, ``token``,
  ``password``, ``credential``, ...) is rejected outright, anywhere in the
  document -- the CLI never accepts a credential in a config file. Binance
  credentials come from ``TRADING_FRAMEWORK_BINANCE_API_KEY`` only.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from trading_cli.errors import ConfigError

_REQUIRED_TOP_LEVEL_KEYS = frozenset({"version", "storage_root"})
_OPTIONAL_TOP_LEVEL_KEYS = frozenset({"data", "research", "dry_run", "report"})
_ALLOWED_TOP_LEVEL_KEYS = _REQUIRED_TOP_LEVEL_KEYS | _OPTIONAL_TOP_LEVEL_KEYS

_SUPPORTED_VERSIONS = frozenset({1})

# Per-block allowed keys (D-S046-07). Keyed by dotted path for readability in
# error messages.
_ALLOWED_KEYS_BY_BLOCK: dict[str, frozenset[str]] = {
    "data": frozenset({"provider", "binance", "databento"}),
    "data.binance": frozenset(
        {"mode", "symbol", "instrument_id", "interval", "start", "end", "publish"}
    ),
    "data.databento": frozenset({"archive", "instrument_id"}),
    "research": frozenset({"kind", "predictive", "strategy"}),
    "research.predictive": frozenset({"definition", "estimator", "persist", "render_report"}),
    "research.strategy": frozenset({"dataset_ref", "timeframe", "strategy_file"}),
    "dry_run": frozenset({"symbol", "duration_minutes", "event_log"}),
    "report": frozenset({"kind", "run_id", "output"}),
}

# Field names that look like a credential, wherever they appear in the
# document. Substring match, case-insensitive (D-S046-08).
_CREDENTIAL_KEY_MARKERS = ("key", "secret", "token", "password", "credential")


@dataclass(frozen=True, slots=True)
class CliConfig:
    """A validated, resolved `trading-cli` config document."""

    version: int
    storage_root: Path
    data: dict[str, Any] | None
    research: dict[str, Any] | None
    dry_run: dict[str, Any] | None
    report: dict[str, Any] | None


def load_config(path: Path) -> CliConfig:
    """Load and strictly validate a config file. Raises `ConfigError` on failure.

    No side effect is performed against `storage_root` or any block: this
    function only parses and validates the document.
    """
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"could not read config file {path}: {exc}") from exc

    try:
        document = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc

    if document is None:
        raise ConfigError(f"config file is empty: {path}")
    if not isinstance(document, dict):
        raise ConfigError(f"config file must be a YAML mapping at the top level: {path}")

    _reject_credential_shaped_keys(document)
    return _validate(document)


def _reject_credential_shaped_keys(node: Any, path: str = "") -> None:
    """Recursively reject any key that looks like a credential (D-S046-08)."""
    if isinstance(node, dict):
        for key, value in node.items():
            key_path = f"{path}.{key}" if path else str(key)
            if isinstance(key, str) and _looks_like_credential_key(key):
                raise ConfigError(
                    f"config key '{key_path}' looks like a credential and is rejected; "
                    "no credential belongs in a config file -- use an environment "
                    "variable instead (e.g. TRADING_FRAMEWORK_BINANCE_API_KEY)"
                )
            _reject_credential_shaped_keys(value, key_path)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _reject_credential_shaped_keys(item, f"{path}[{index}]")


def _looks_like_credential_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in _CREDENTIAL_KEY_MARKERS)


def _validate(document: dict[str, Any]) -> CliConfig:
    _check_keys(document.keys(), _ALLOWED_TOP_LEVEL_KEYS, "<top level>")

    missing = _REQUIRED_TOP_LEVEL_KEYS - document.keys()
    if missing:
        raise ConfigError(f"config is missing required key(s): {', '.join(sorted(missing))}")

    version = document["version"]
    if version not in _SUPPORTED_VERSIONS:
        supported = ", ".join(str(v) for v in sorted(_SUPPORTED_VERSIONS))
        raise ConfigError(f"unsupported config version {version!r}; supported: {supported}")

    storage_root_raw = document["storage_root"]
    if not isinstance(storage_root_raw, str) or not storage_root_raw.strip():
        raise ConfigError("'storage_root' must be a non-empty string")

    data_block = _validate_block(document.get("data"), "data")
    research_block = _validate_block(document.get("research"), "research")
    dry_run_block = _validate_block(document.get("dry_run"), "dry_run")
    report_block = _validate_block(document.get("report"), "report")

    if data_block is not None:
        _validate_nested_provider_block(data_block, "data", "provider")
    if research_block is not None:
        _validate_nested_provider_block(research_block, "research", "kind")

    return CliConfig(
        version=version,
        storage_root=Path(storage_root_raw),
        data=data_block,
        research=research_block,
        dry_run=dry_run_block,
        report=report_block,
    )


def _validate_block(block: Any, name: str) -> dict[str, Any] | None:
    if block is None:
        return None
    if not isinstance(block, dict):
        raise ConfigError(f"config block '{name}' must be a mapping")
    _check_keys(block.keys(), _ALLOWED_KEYS_BY_BLOCK[name], name)
    return block


def _validate_nested_provider_block(block: dict[str, Any], name: str, selector_key: str) -> None:
    """Validate a `data`/`research` block's provider-/kind-selected sub-block.

    e.g. `data.provider: binance` selects and validates `data.binance`;
    `research.kind: predictive` selects and validates `research.predictive`.
    """
    selector = block.get(selector_key)
    if selector is None:
        return
    nested_path = f"{name}.{selector}"
    if nested_path not in _ALLOWED_KEYS_BY_BLOCK:
        supported = sorted(
            key.removeprefix(f"{name}.")
            for key in _ALLOWED_KEYS_BY_BLOCK
            if key.startswith(f"{name}.")
        )
        raise ConfigError(
            f"unsupported '{name}.{selector_key}': {selector!r}; supported: {', '.join(supported)}"
        )
    nested = block.get(selector)
    if nested is None:
        return
    if not isinstance(nested, dict):
        raise ConfigError(f"config block '{nested_path}' must be a mapping")
    _check_keys(nested.keys(), _ALLOWED_KEYS_BY_BLOCK[nested_path], nested_path)


def _check_keys(actual: Any, allowed: frozenset[str], path: str) -> None:
    unknown = sorted(set(actual) - allowed)
    if not unknown:
        return
    offending = unknown[0]
    closest = difflib.get_close_matches(offending, sorted(allowed), n=1)
    suggestion = f"; closest valid key: '{closest[0]}'" if closest else ""
    raise ConfigError(f"unknown config key '{offending}' in '{path}'{suggestion}")
