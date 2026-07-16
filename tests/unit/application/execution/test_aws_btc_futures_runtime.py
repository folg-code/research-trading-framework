"""Tests for AWS BTC futures dry-run runtime configuration."""

import asyncio
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from trading_framework.application.execution import (
    AwsBtcFuturesRuntimeConfig,
    RunLocalBtcFuturesBinanceDryRunResult,
    create_aws_execution_state_repository,
    load_aws_btc_futures_runtime_config,
    run_aws_btc_futures_dry_run,
)
from trading_framework.core.exceptions import ConfigurationError
from trading_framework.infrastructure.storage.dynamodb_execution_state import (
    DynamoDbExecutionStateRepository,
)
from trading_framework.infrastructure.storage.execution_state import JsonExecutionStateRepository


def test_load_aws_btc_futures_runtime_config_builds_dry_run_request() -> None:
    config = load_aws_btc_futures_runtime_config(
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND": "local",
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
    assert config.execution_state_backend == "local"
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
    assert config.execution_state_backend == "dynamodb"
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
        {
            "TRADING_FRAMEWORK_AWS_REGION": "eu-central-1",
            "TRADING_FRAMEWORK_EXECUTION_STATE_TABLE": "demo-execution-state",
            "TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND": "sqlite",
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


def test_create_aws_execution_state_repository_uses_local_backend(tmp_path: Path) -> None:
    repository = create_aws_execution_state_repository(
        AwsBtcFuturesRuntimeConfig(
            aws_region="eu-central-1",
            execution_state_table_name="demo-execution-state",
            execution_state_backend="local",
            state_repository_path=tmp_path,
        )
    )

    assert isinstance(repository, JsonExecutionStateRepository)
    assert repository.base_path == tmp_path


def test_create_aws_execution_state_repository_uses_dynamodb_backend() -> None:
    fake_client = FakeDynamoDbClient()

    repository = create_aws_execution_state_repository(
        AwsBtcFuturesRuntimeConfig(
            aws_region="eu-central-1",
            execution_state_table_name="demo-execution-state",
        ),
        dynamodb_client=fake_client,
    )

    assert isinstance(repository, DynamoDbExecutionStateRepository)
    assert repository.table_name == "demo-execution-state"
    assert cast(Any, repository).client is fake_client


def test_run_aws_btc_futures_dry_run_passes_repository_to_binance_loop() -> None:
    fake_client = FakeDynamoDbClient()
    config = AwsBtcFuturesRuntimeConfig(
        aws_region="eu-central-1",
        execution_state_table_name="demo-execution-state",
    )
    captured: dict[str, Any] = {}

    async def fake_run(
        request: Any,
        *,
        state_repository: Any,
    ) -> RunLocalBtcFuturesBinanceDryRunResult:
        assert request.config.runtime_id == "btc-futures-dry-run-aws"
        assert isinstance(state_repository, DynamoDbExecutionStateRepository)
        captured["state_repository"] = state_repository
        return cast(RunLocalBtcFuturesBinanceDryRunResult, object())

    with (
        patch(
            "trading_framework.application.execution.aws_btc_futures_runtime._create_boto3_dynamodb_client",
            return_value=fake_client,
        ),
        patch(
            "trading_framework.application.execution.aws_btc_futures_runtime.run_local_btc_futures_binance_dry_run",
            fake_run,
        ),
    ):
        asyncio.run(run_aws_btc_futures_dry_run(config))

    assert cast(Any, captured["state_repository"]).client is fake_client


class FakeDynamoDbClient:
    def get_item(
        self,
        *,
        TableName: str,
        Key: Mapping[str, Mapping[str, str]],
        ConsistentRead: bool = False,
    ) -> Mapping[str, Any]:
        return {}

    def put_item(
        self,
        *,
        TableName: str,
        Item: Mapping[str, Mapping[str, str]],
    ) -> Mapping[str, Any]:
        return {}
