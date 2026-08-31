"""`trading-cli data fetch` (S046-T009/T010, not implemented in Wave 1)."""

from __future__ import annotations

from pathlib import Path

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, NotImplementedCommandError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_PROVIDERS = ("binance", "databento")


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.data is None:
        raise ConfigError("config is missing the 'data' block required by 'data fetch'")
    provider = config.data.get("provider")
    if provider not in _SUPPORTED_PROVIDERS:
        raise ConfigError(
            f"unsupported 'data.provider': {provider!r}; "
            f"supported: {', '.join(_SUPPORTED_PROVIDERS)}"
        )
    provider_args = dict(config.data.get(provider) or {})
    output_path = str(Path(config.storage_root) / "market_data")
    return ResolvedPlan(
        group="data",
        command="fetch",
        workflow=f"data.fetch.{provider}",
        arguments={"provider": provider, **provider_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=False,
    )


def run(plan: ResolvedPlan) -> None:
    provider = plan.arguments.get("provider")
    raise NotImplementedCommandError(
        f"'data fetch {provider}' is not implemented yet (Wave 1 skeleton); "
        "see SPRINT_046.md Wave 2 (S046-T009/T010)"
    )
