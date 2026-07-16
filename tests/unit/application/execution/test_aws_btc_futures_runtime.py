"""Tests for AWS BTC futures dry-run runtime configuration."""

from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.execution import (
    AwsBtcFuturesRuntimeConfig,
    load_aws_btc_futures_runtime_config,
)
from trading_framework.core.exceptions import ConfigurationError


def test_load_aws_btc_futures_runtime_config_builds_dry_run_request() -> None:
    config = load_aws_btc_futures_runtime_config(
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_RUNTIME_ID": "aws-runtime-1",
            "TRADING_FRAMEWORK_SYMBOL": "btcusdt",
            "TRADING_FRAMEWORK_EVENT_LOG_PATH": "/tmp/events.jsonl",
            "TRADING_FRAMEWORK_STATE_REPOSITORY_PATH": "/tmp/state",
            "TRADING_FRAMEWORK_STARTING_EQUITY": "25000",
            "TRADING_FRAMEWORK_QUANTITY": "0.002",
            "TRADING_FRAMEWORK_EMA_PERIOD": "12",
            "TRADING_FRAMEWORK_EXIT_AFTER_BARS": "4",
            "TRADING_FRAMEWORK_DURATION_SECONDS": "120",
            "TRADING_FRAMEWORK_HEARTBEAT_SECONDS": "5",
            "TRADING_FRAMEWORK_MAX_CLOSED_BARS": "50",
            "TRADING_FRAMEWORK_MAX_MESSAGES": "10",
        }
    )

    request = config.to_binance_dry_run_request()

    assert config.aws_region == "eu-central-1"
    assert config.execution_state_table_name == "demo-execution-state"
    assert request.config.runtime_id == "aws-runtime-1"
    assert request.config.symbol == "BTCUSDT"
    assert request.config.event_log_path == Path("/tmp/events.jsonl")
    assert request.config.state_repository_path == Path("/tmp/state")
    assert request.config.starting_equity == Decimal("25000")
    assert request.config.strategy_config is not None
    assert request.config.strategy_config.quantity == Decimal("0.002")
    assert request.config.strategy_config.ema_period == 12
    assert request.config.strategy_config.exit_after_bars == 4
    assert request.duration_seconds == 120
    assert request.heartbeat_seconds == 5
    assert request.max_closed_bars == 50
    assert request.max_messages == 10


def test_load_aws_btc_futures_runtime_config_uses_safe_defaults() -> None:
    config = load_aws_btc_futures_runtime_config(
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
        }
    )

    assert config.runtime_id == "btc-futures-dry-run-aws"
    assert config.symbol == "BTCUSDT"
    assert config.duration_seconds == 3600
    assert config.heartbeat_seconds == 30
    assert config.max_messages is None


@pytest.mark.parametrize(
    "env",
    [
        {},
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
        },
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_QUANTITY": "0",
        },
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_MAX_MESSAGES": "0",
        },
    ],
)
def test_load_aws_btc_futures_runtime_config_rejects_invalid_env(
    env: dict[str, str],
) -> None:
    with pytest.raises(ConfigurationError):
        load_aws_btc_futures_runtime_config(env)


def test_aws_btc_futures_runtime_config_rejects_blank_values() -> None:
    with pytest.raises(ConfigurationError, match="AWS_REGION"):
        AwsBtcFuturesRuntimeConfig(
            aws_region=" ",
            execution_state_table_name="demo-execution-state",
        )
