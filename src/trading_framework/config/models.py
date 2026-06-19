"""Framework configuration models."""

from enum import StrEnum
from typing import final

from pydantic import BaseModel, ConfigDict, Field


class Environment(StrEnum):
    """Supported runtime environments."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


@final
class FrameworkConfig(BaseModel):
    """Minimal validated framework configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Environment = Environment.DEV
    log_level: str = Field(default="INFO", min_length=1)
