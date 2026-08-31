"""`trading-cli report render` (S046-T005, not implemented in Wave 1)."""

from __future__ import annotations

from pathlib import Path

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, NotImplementedCommandError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_KINDS = ("predictive", "strategy")


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.report is None:
        raise ConfigError("config is missing the 'report' block required by 'report render'")
    kind = config.report.get("kind")
    if kind not in _SUPPORTED_KINDS:
        raise ConfigError(
            f"unsupported 'report.kind': {kind!r}; supported: {', '.join(_SUPPORTED_KINDS)}"
        )
    args = dict(config.report)
    output = args.get("output") or str(Path(config.storage_root) / "reports" / str(kind))
    return ResolvedPlan(
        group="report",
        command="render",
        workflow=f"report.render.{kind}",
        arguments=args,
        output_paths=(str(output),),
        storage_root=str(config.storage_root),
        implemented=False,
    )


def run(plan: ResolvedPlan) -> None:
    kind = plan.arguments.get("kind")
    raise NotImplementedCommandError(
        f"'report render {kind}' is not implemented yet (Wave 1 skeleton); "
        "see SPRINT_046.md Wave 2 (S046-T005)"
    )
