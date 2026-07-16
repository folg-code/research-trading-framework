"""Tests for the AWS status API Lambda wrapper."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

from scripts.execution import aws_status_api_handler


def test_lambda_handler_delegates_to_application_handler() -> None:
    event = {"httpMethod": "GET"}
    expected = {"statusCode": 200, "headers": {}, "body": "{}"}

    def fake_handler(received_event: dict[str, Any], env: object) -> dict[str, Any]:
        assert received_event == event
        assert env is os.environ
        return expected

    with patch.object(
        aws_status_api_handler,
        "handle_aws_execution_status_api_request",
        fake_handler,
    ):
        response = aws_status_api_handler.lambda_handler(event, object())

    assert response == expected
