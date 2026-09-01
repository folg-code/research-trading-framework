"""Tests for the YAML config loader and strict validation (S046-T002)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trading_cli.config import CliConfig, load_config
from trading_cli.errors import ConfigError

_VALID_CONFIG = """
version: 1
storage_root: user_data/workspace

data:
  provider: binance
  binance:
    mode: ohlcv
    symbol: BTCUSDT
    instrument_id: BTCUSDT.P
    interval: 1m
    start: 2025-01-01T00:00:00Z
    end: 2025-04-01T00:00:00Z
    publish: true

research:
  kind: predictive
  predictive:
    definition: configs/study.yaml
    estimator: configs/ridge.yaml
    persist: true
    render_report: true

dry_run:
  symbol: BTCUSDT
  duration_minutes: 60
  event_log: user_data/runtime/btc_futures_dry_run/events.jsonl

report:
  kind: predictive
  run_id: some-run-id
  output: user_data/reports/predictive.html
"""


def _write(tmp_path: Path, text: str, name: str = "config.yaml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_config_loads(tmp_path: Path) -> None:
    path = _write(tmp_path, _VALID_CONFIG)

    config = load_config(path)

    assert isinstance(config, CliConfig)
    assert config.version == 1
    assert config.storage_root == Path("user_data/workspace")
    assert config.data is not None
    assert config.data["provider"] == "binance"
    assert config.research is not None
    assert config.research["kind"] == "predictive"
    assert config.dry_run is not None
    assert config.dry_run["symbol"] == "BTCUSDT"
    assert config.report is not None
    assert config.report["run_id"] == "some-run-id"


def test_minimal_config_loads(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: 1\nstorage_root: user_data/workspace\n")

    config = load_config(path)

    assert config.version == 1
    assert config.data is None
    assert config.research is None
    assert config.dry_run is None
    assert config.report is None


def test_missing_required_key_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: 1\n")

    with pytest.raises(ConfigError, match="storage_root"):
        load_config(path)


def test_missing_both_required_keys_fails(tmp_path: Path) -> None:
    path = _write(tmp_path, "data:\n  provider: binance\n")

    with pytest.raises(ConfigError, match="version"):
        load_config(path)


def test_unknown_top_level_key_rejected_with_suggestion(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 1\nstorage_root: user_data/workspace\nstoragre_root_typo: oops\n",
    )

    with pytest.raises(ConfigError, match="storagre_root_typo"):
        load_config(path)


def test_unknown_nested_key_names_offending_key(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
storage_root: user_data/workspace
data:
  provider: binance
  binance:
    symbol: BTCUSDT
    intervall: 1m
""",
    )

    with pytest.raises(ConfigError, match="intervall"):
        load_config(path)


def test_research_strategy_strategy_file_key_is_accepted(tmp_path: Path) -> None:
    """S047-T001: `research.strategy.strategy_file` is a recognised, optional key."""
    path = _write(
        tmp_path,
        (
            "version: 1\nstorage_root: user_data/workspace\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            "    dataset_ref: 'BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1'\n"
            "    timeframe: 1m\n"
            "    strategy_file: user_data/components/strategies/my_strategy.py\n"
        ),
    )

    config = load_config(path)

    assert config.research is not None
    assert (
        config.research["strategy"]["strategy_file"]
        == "user_data/components/strategies/my_strategy.py"
    )


def test_research_strategy_strategy_path_typo_is_rejected(tmp_path: Path) -> None:
    """S047-T001: a mistyped `strategy_path` is still rejected by name, not silently accepted."""
    path = _write(
        tmp_path,
        (
            "version: 1\nstorage_root: user_data/workspace\n"
            "research:\n"
            "  kind: strategy\n"
            "  strategy:\n"
            "    dataset_ref: 'BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1'\n"
            "    strategy_path: user_data/components/strategies/my_strategy.py\n"
        ),
    )

    with pytest.raises(ConfigError, match="strategy_path"):
        load_config(path)


def test_unknown_key_suggests_closest_match(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 1\nstorage_root: user_data/workspace\nresearh:\n  kind: predictive\n",
    )

    with pytest.raises(ConfigError, match="closest valid key: 'research'"):
        load_config(path)


@pytest.mark.parametrize(
    "credential_key",
    ["api_key", "secret", "token", "password", "credential", "client_secret"],
)
def test_credential_shaped_key_rejected(tmp_path: Path, credential_key: str) -> None:
    path = _write(
        tmp_path,
        f"version: 1\nstorage_root: user_data/workspace\n{credential_key}: shh\n",
    )

    with pytest.raises(ConfigError, match="credential"):
        load_config(path)


def test_credential_shaped_key_rejected_when_nested(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
version: 1
storage_root: user_data/workspace
data:
  provider: binance
  binance:
    symbol: BTCUSDT
    api_key: shh
""",
    )

    with pytest.raises(ConfigError, match="credential"):
        load_config(path)


def test_unsupported_version_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: 2\nstorage_root: user_data/workspace\n")

    with pytest.raises(ConfigError, match="version"):
        load_config(path)


def test_invalid_yaml_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: [1\nstorage_root: user_data/workspace\n")

    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.yaml")


def test_non_mapping_document_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path, "- 1\n- 2\n")

    with pytest.raises(ConfigError, match="mapping"):
        load_config(path)


def test_unsupported_provider_rejected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 1\nstorage_root: user_data/workspace\ndata:\n  provider: coinbase\n",
    )

    with pytest.raises(ConfigError, match="provider"):
        load_config(path)
