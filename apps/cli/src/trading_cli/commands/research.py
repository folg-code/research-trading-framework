"""`trading-cli research run` (S046-T006/T007, not implemented in Wave 1)."""

from __future__ import annotations

from pathlib import Path

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, NotImplementedCommandError
from trading_cli.plan import ResolvedPlan

_SUPPORTED_KINDS = ("predictive", "strategy")


def resolve_plan(config: CliConfig) -> ResolvedPlan:
    if config.research is None:
        raise ConfigError("config is missing the 'research' block required by 'research run'")
    kind = config.research.get("kind")
    if kind not in _SUPPORTED_KINDS:
        raise ConfigError(
            f"unsupported 'research.kind': {kind!r}; supported: {', '.join(_SUPPORTED_KINDS)}"
        )
    kind_args = dict(config.research.get(kind) or {})
    output_path = str(Path(config.storage_root) / "research" / kind)
    return ResolvedPlan(
        group="research",
        command="run",
        workflow=f"research.run.{kind}",
        arguments={"kind": kind, **kind_args},
        output_paths=(output_path,),
        storage_root=str(config.storage_root),
        implemented=False,
    )


def run(plan: ResolvedPlan) -> None:
    kind = plan.arguments.get("kind")
    raise NotImplementedCommandError(
        f"'research run {kind}' is not implemented yet (Wave 1 skeleton); "
        "see SPRINT_046.md Wave 2 (S046-T006/T007)"
    )
