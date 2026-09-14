"""workbench-api entry point (``uv run --package trading-workbench workbench-api``)."""

from __future__ import annotations

import asyncio
import os
import sys

from trading_framework.core.exceptions import ConfigurationError

from workbench_core.app import run_app
from workbench_core.config import load_workbench_api_config


def main(argv: list[str] | None = None) -> int:
    """Run workbench-api until interrupted."""
    del argv  # environment-only configuration, matching run_vps_status_service.py
    try:
        config = load_workbench_api_config(dict(os.environ))
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    asyncio.run(run_app(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
