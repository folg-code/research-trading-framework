"""Read-only AWS status API handler for the BTC futures dry-run demo."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, final

from trading_framework.application.execution.aws_btc_futures_runtime import (
    AwsBtcFuturesRuntimeConfig,
    create_aws_execution_state_repository,
    load_aws_btc_futures_runtime_config,
)
from trading_framework.application.execution.status_json import runtime_status_view_to_json
from trading_framework.core.exceptions import (
    ConfigurationError,
    TradingFrameworkError,
    ValidationError,
)
from trading_framework.execution import (
    DEFAULT_RECENT_EVENT_LIMIT,
    DEFAULT_RECENT_FILL_LIMIT,
    DEFAULT_RECENT_ORDER_LIMIT,
    ExecutionReadModelQuery,
    ExecutionStateRepository,
)
from trading_framework.infrastructure.storage.dynamodb_execution_state import (
    DynamoDbExecutionStateClient,
)

DEFAULT_STATUS_API_CORS_ORIGIN = "*"


@final
@dataclass(frozen=True, slots=True)
class AwsExecutionStatusApiConfig:
    """Read-only execution status API configuration."""

    runtime_config: AwsBtcFuturesRuntimeConfig
    cors_origin: str = DEFAULT_STATUS_API_CORS_ORIGIN
    recent_event_limit: int = DEFAULT_RECENT_EVENT_LIMIT
    recent_order_limit: int = DEFAULT_RECENT_ORDER_LIMIT
    recent_fill_limit: int = DEFAULT_RECENT_FILL_LIMIT

    def __post_init__(self) -> None:
        if not self.cors_origin.strip():
            raise ConfigurationError("STATUS_API_CORS_ORIGIN must be non-empty")
        _require_positive_limit(self.recent_event_limit, "STATUS_API_RECENT_EVENTS")
        _require_positive_limit(self.recent_order_limit, "STATUS_API_RECENT_ORDERS")
        _require_positive_limit(self.recent_fill_limit, "STATUS_API_RECENT_FILLS")

    @property
    def runtime_id(self) -> str:
        """Runtime id exposed by this read-only API."""
        return self.runtime_config.runtime_id


def load_aws_execution_status_api_config(
    env: Mapping[str, str],
) -> AwsExecutionStatusApiConfig:
    """Load the read-only status API configuration from environment variables."""
    return AwsExecutionStatusApiConfig(
        runtime_config=load_aws_btc_futures_runtime_config(env),
        cors_origin=_optional(env, "STATUS_API_CORS_ORIGIN", DEFAULT_STATUS_API_CORS_ORIGIN),
        recent_event_limit=_int(env, "STATUS_API_RECENT_EVENTS", DEFAULT_RECENT_EVENT_LIMIT),
        recent_order_limit=_int(env, "STATUS_API_RECENT_ORDERS", DEFAULT_RECENT_ORDER_LIMIT),
        recent_fill_limit=_int(env, "STATUS_API_RECENT_FILLS", DEFAULT_RECENT_FILL_LIMIT),
    )


def handle_aws_execution_status_api_request(
    event: Mapping[str, Any],
    env: Mapping[str, str],
    *,
    repository: ExecutionStateRepository | None = None,
    dynamodb_client: DynamoDbExecutionStateClient | None = None,
) -> dict[str, Any]:
    """Handle one read-only API Gateway/Lambda execution status request."""
    try:
        config = load_aws_execution_status_api_config(env)
        if _request_method(event) != "GET":
            return _response(
                405,
                {"error": "method_not_allowed", "message": "only GET is supported"},
                cors_origin=config.cors_origin,
                extra_headers={"Allow": "GET"},
            )
        state_repository = repository or create_aws_execution_state_repository(
            config.runtime_config,
            dynamodb_client=dynamodb_client,
        )
        query = ExecutionReadModelQuery(
            runtime_id=config.runtime_id,
            recent_event_limit=config.recent_event_limit,
            recent_order_limit=config.recent_order_limit,
            recent_fill_limit=config.recent_fill_limit,
        )
        status = state_repository.latest_status_view(query)
    except (ConfigurationError, TradingFrameworkError, ValidationError) as exc:
        return _response(
            500,
            {"error": "status_unavailable", "message": str(exc), "simulated": True},
            cors_origin=DEFAULT_STATUS_API_CORS_ORIGIN,
        )

    if status is None:
        return _response(
            404,
            {
                "error": "runtime_status_not_found",
                "runtime_id": query.runtime_id,
                "simulated": True,
            },
            cors_origin=config.cors_origin,
        )
    return _response(200, runtime_status_view_to_json(status), cors_origin=config.cors_origin)


def _response(
    status_code: int,
    payload: Mapping[str, Any],
    *,
    cors_origin: str,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": cors_origin,
        "Cache-Control": "no-store",
    }
    if extra_headers is not None:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(dict(payload), sort_keys=True),
    }


def _request_method(event: Mapping[str, Any]) -> str:
    request_context = event.get("requestContext")
    if isinstance(request_context, Mapping):
        http = request_context.get("http")
        if isinstance(http, Mapping):
            method = http.get("method")
            if isinstance(method, str):
                return method.upper()
    method = event.get("httpMethod")
    if isinstance(method, str):
        return method.upper()
    return "GET"


def _optional(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(f"TRADING_FRAMEWORK_{name}")
    if value is None or not value.strip():
        return default
    return value


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _optional(env, name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"TRADING_FRAMEWORK_{name} must be an integer") from exc


def _require_positive_limit(value: int, field_name: str) -> None:
    if value < 1:
        raise ConfigurationError(f"{field_name} must be positive")
