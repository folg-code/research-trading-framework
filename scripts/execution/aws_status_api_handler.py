"""AWS Lambda handler for the read-only BTC futures dry-run status API."""

from __future__ import annotations

import os
from typing import Any

from trading_framework.application.execution import handle_aws_execution_status_api_request


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Handle API Gateway requests for the latest simulated execution status."""
    return handle_aws_execution_status_api_request(event, os.environ)
