"""AWS Lambda handler for the read-only BTC futures dry-run status API.

This module intentionally avoids importing ``trading_framework`` package entrypoints. Lambda imports
the handler during cold start, and package-level execution imports pull in research/runtime modules
that are unnecessary for a read-only DynamoDB status lookup.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

DEFAULT_STATUS_API_CORS_ORIGIN = "*"
DEFAULT_RECENT_EVENT_LIMIT = 50
DEFAULT_RECENT_ORDER_LIMIT = 20
DEFAULT_RECENT_FILL_LIMIT = 20
STATE_SORT_KEY = "STATE"
STATE_VERSION = 1


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Handle API Gateway requests for the latest simulated execution status."""
    return handle_aws_execution_status_api_request(event, os.environ)


def handle_aws_execution_status_api_request(
    event: Mapping[str, Any],
    env: Mapping[str, str],
    *,
    dynamodb_client: Any | None = None,
) -> dict[str, Any]:
    """Return the latest public dry-run status directly from the DynamoDB state item."""
    cors_origin = _optional(env, "STATUS_API_CORS_ORIGIN", DEFAULT_STATUS_API_CORS_ORIGIN)
    try:
        if _request_method(event) != "GET":
            return _response(
                405,
                {"error": "method_not_allowed", "message": "only GET is supported"},
                cors_origin=cors_origin,
                extra_headers={"Allow": "GET"},
            )
        region = _required(env, "AWS_REGION")
        table_name = _required(env, "EXECUTION_STATE_TABLE")
        runtime_id = _optional(env, "RUNTIME_ID", "btc-futures-dry-run-aws")
        recent_event_limit = _int(env, "STATUS_API_RECENT_EVENTS", DEFAULT_RECENT_EVENT_LIMIT)
        recent_order_limit = _int(env, "STATUS_API_RECENT_ORDERS", DEFAULT_RECENT_ORDER_LIMIT)
        recent_fill_limit = _int(env, "STATUS_API_RECENT_FILLS", DEFAULT_RECENT_FILL_LIMIT)
        client = dynamodb_client or _create_dynamodb_client(region)
        state = _load_state(client=client, table_name=table_name, runtime_id=runtime_id)
    except (KeyError, TypeError, ValueError) as exc:
        return _response(
            500,
            {"error": "status_unavailable", "message": str(exc), "simulated": True},
            cors_origin=cors_origin,
        )

    status = state.get("status")
    if not isinstance(status, Mapping):
        return _response(
            404,
            {
                "error": "runtime_status_not_found",
                "runtime_id": runtime_id,
                "simulated": True,
            },
            cors_origin=cors_origin,
        )
    return _response(
        200,
        _status_payload(
            runtime_id=runtime_id,
            status=status,
            state=state,
            recent_event_limit=recent_event_limit,
            recent_order_limit=recent_order_limit,
            recent_fill_limit=recent_fill_limit,
        ),
        cors_origin=cors_origin,
    )


def _create_dynamodb_client(region: str) -> Any:
    import boto3  # type: ignore[import-untyped]

    return boto3.client("dynamodb", region_name=region)


def _load_state(*, client: Any, table_name: str, runtime_id: str) -> dict[str, Any]:
    response = client.get_item(
        TableName=table_name,
        Key={
            "pk": {"S": f"RUNTIME#{runtime_id}"},
            "sk": {"S": STATE_SORT_KEY},
        },
        ConsistentRead=True,
    )
    item = response.get("Item")
    if item is None:
        return _empty_state()
    if _number_attribute(item, "version") != STATE_VERSION:
        raise ValueError("unsupported DynamoDB execution state version")
    payload = json.loads(_string_attribute(item, "state_json"))
    if not isinstance(payload, dict):
        raise ValueError("DynamoDB state_json must contain an object")
    return {
        "status": payload.get("status"),
        "events": list(payload.get("events", ())),
        "orders": list(payload.get("orders", ())),
        "fills": list(payload.get("fills", ())),
        "position": payload.get("position"),
        "account": payload.get("account"),
    }


def _status_payload(
    *,
    runtime_id: str,
    status: Mapping[str, Any],
    state: Mapping[str, Any],
    recent_event_limit: int,
    recent_order_limit: int,
    recent_fill_limit: int,
) -> dict[str, Any]:
    position = state.get("position")
    account = state.get("account")
    return {
        "runtime_id": runtime_id,
        "mode": status.get("mode"),
        "provider": status.get("provider"),
        "symbol": status.get("symbol"),
        "status": status.get("status"),
        "generated_at": datetime.now(UTC).isoformat(),
        "last_heartbeat_at": status.get("last_heartbeat_at"),
        "last_market_event_at": status.get("last_market_event_at"),
        "last_price": _mapping_value(position, "mark_price"),
        "current_signal": status.get("current_signal"),
        "current_position": position,
        "paper_equity": _mapping_value(account, "equity"),
        "realized_pnl": _mapping_value(account, "realized_pnl"),
        "unrealized_pnl": _mapping_value(account, "unrealized_pnl"),
        "recent_orders": _tail(state.get("orders"), recent_order_limit),
        "recent_fills": _tail(state.get("fills"), recent_fill_limit),
        "recent_events": _tail(state.get("events"), recent_event_limit),
        "simulated": True,
    }


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


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(f"TRADING_FRAMEWORK_{name}")
    if value is None or not value.strip():
        raise ValueError(f"TRADING_FRAMEWORK_{name} is required")
    return value


def _optional(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(f"TRADING_FRAMEWORK_{name}")
    if value is None or not value.strip():
        return default
    return value


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _optional(env, name, str(default))
    value = int(raw)
    if value < 1:
        raise ValueError(f"TRADING_FRAMEWORK_{name} must be positive")
    return value


def _string_attribute(item: Mapping[str, Any], name: str) -> str:
    value = item.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"DynamoDB attribute {name} must be present")
    raw = value.get("S")
    if not isinstance(raw, str):
        raise ValueError(f"DynamoDB attribute {name} must be a string")
    return raw


def _number_attribute(item: Mapping[str, Any], name: str) -> int:
    value = item.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"DynamoDB attribute {name} must be present")
    raw = value.get("N")
    if not isinstance(raw, str):
        raise ValueError(f"DynamoDB attribute {name} must be a number")
    return int(raw)


def _tail(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[-limit:]


def _mapping_value(value: Any, key: str) -> Any:
    if not isinstance(value, Mapping):
        return None
    return value.get(key)


def _empty_state() -> dict[str, Any]:
    return {
        "status": None,
        "events": [],
        "orders": [],
        "fills": [],
        "position": None,
        "account": None,
    }
