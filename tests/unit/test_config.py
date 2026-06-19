"""Framework configuration tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from trading_framework.config import FrameworkConfig, configure_logging, load_framework_config
from trading_framework.config.models import Environment
from trading_framework.core.exceptions import ConfigurationError


def test_framework_config_defaults() -> None:
    config = FrameworkConfig()
    assert config.environment is Environment.DEV
    assert config.log_level == "INFO"


def test_framework_config_rejects_unknown_fields() -> None:
    with pytest.raises(PydanticValidationError):
        FrameworkConfig.model_validate({"unknown": True})


def test_load_framework_config_reads_valid_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "framework.toml"
    config_path.write_text(
        'environment = "test"\nlog_level = "DEBUG"\n',
        encoding="utf-8",
    )
    config = load_framework_config(config_path)
    assert config.environment is Environment.TEST
    assert config.log_level == "DEBUG"


def test_load_framework_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        load_framework_config(tmp_path / "missing.toml")


def test_load_framework_config_rejects_invalid_schema(tmp_path: Path) -> None:
    config_path = tmp_path / "framework.toml"
    config_path.write_text('environment = "invalid"\n', encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_framework_config(config_path)


def test_configure_logging_uses_config_level() -> None:
    config = FrameworkConfig(log_level="WARNING")
    configure_logging(config)
