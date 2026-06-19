"""Configuration file loading."""

import tomllib
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from trading_framework.config.models import FrameworkConfig
from trading_framework.core.exceptions import ConfigurationError


def load_framework_config(path: Path) -> FrameworkConfig:
    """Load framework configuration from a TOML file."""
    if not path.is_file():
        msg = f"configuration file not found: {path}"
        raise ConfigurationError(msg)

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        msg = f"malformed configuration file: {path}"
        raise ConfigurationError(msg) from exc

    try:
        return FrameworkConfig.model_validate(raw)
    except PydanticValidationError as exc:
        msg = f"invalid configuration schema: {path}"
        raise ConfigurationError(msg) from exc
