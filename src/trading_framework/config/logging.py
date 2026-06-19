"""Logging configuration."""

import logging

from trading_framework.config.models import FrameworkConfig


def configure_logging(config: FrameworkConfig) -> None:
    """Configure root logging from framework configuration."""
    level = logging.getLevelNamesMapping().get(config.log_level.upper())
    if level is None:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
