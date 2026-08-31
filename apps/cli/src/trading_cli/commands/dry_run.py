"""`trading-cli dry-run start` (S046-T008, not implemented in Wave 1)."""

from __future__ import annotations

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, NotImplementedCommandError
from trading_cli.plan import ResolvedPlan


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.dry_run is None:
        raise ConfigError("config is missing the 'dry_run' block required by 'dry-run start'")
    args = dict(config.dry_run)
    event_log = args.get("event_log")
    output_paths = (str(event_log),) if event_log else ()
    return ResolvedPlan(
        group="dry-run",
        command="start",
        workflow="dry_run.start",
        arguments=args,
        output_paths=output_paths,
        storage_root=str(config.storage_root),
        implemented=False,
    )


def run(plan: ResolvedPlan) -> None:
    raise NotImplementedCommandError(
        "'dry-run start' is not implemented yet (Wave 1 skeleton); "
        "see SPRINT_046.md Wave 2 (S046-T008)"
    )
