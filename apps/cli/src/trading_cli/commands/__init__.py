"""Command-group modules for `trading-cli`.

Each module exposes:

- ``resolve_plan(config: CliConfig) -> ResolvedPlan`` -- pure, no side
  effects; called for both `--dry-run` and real runs.
- ``run(plan: ResolvedPlan) -> None`` -- the actual application-layer call.
  Wave 1 (this package) leaves every ``run`` raising
  ``NotImplementedCommandError``; Wave 2 (S046-T005..T009) fills in the
  bodies, calling `trading_framework.application.*` workflows only.
"""

from __future__ import annotations
