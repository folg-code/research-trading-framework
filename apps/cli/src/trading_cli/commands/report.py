"""`trading-cli report render` (S046-T005).

Pure application calls: this command never fits, predicts, or simulates. It
loads a persisted run (predictive or strategy) and writes the same offline
HTML the underlying scripts already produce
(``scripts/predictive_research/render_predictive_report.py``,
``scripts/strategy_research/render_strategy_dashboard.py``).

Predictive rendering has an application-layer default output path (the run
directory); strategy rendering does not -- ``render_strategy_research_dashboard``
requires an explicit path, so this command supplies the same
``storage_root/reports/strategy/<run_id>.html`` convention documented in
``resolve_plan`` below when the config leaves ``output`` unset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_framework.application.predictive_research import (
    RenderPredictiveReportRequest,
    render_predictive_research_report,
)
from trading_framework.application.strategy_research import (
    BuildStrategyDashboardRequest,
    build_strategy_dashboard_view_model,
)
from trading_framework.core.exceptions import ValidationError

# apps/cli boundary widening (documented in tests/unit/test_apps_boundaries.py
# and apps/cli/CLAUDE.md): these are typed run identifiers, not research logic.
from trading_framework.research.analytics.strategy_dashboard_report import (
    render_strategy_research_dashboard,
)
from trading_framework.research.datasets.predictive_run import PredictiveRunRef
from trading_framework.research.datasets.strategy_research import StrategyResearchRunRef

from trading_cli.config import CliConfig
from trading_cli.errors import ConfigError, WorkflowError
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
    run_id = args.get("run_id")
    if not run_id:
        raise ConfigError("config is missing 'report.run_id' required by 'report render'")

    output = args.get("output")
    if output is None and kind == "strategy":
        output = str(_default_strategy_output(config.storage_root, run_id))
    output_paths = (
        (str(output),) if output else (f"(default report path under the {kind} run directory)",)
    )
    return ResolvedPlan(
        group="report",
        command="render",
        workflow=f"report.render.{kind}",
        arguments=args,
        output_paths=output_paths,
        storage_root=str(config.storage_root),
        implemented=True,
    )


def run(plan: ResolvedPlan) -> dict[str, Any]:
    kind = plan.arguments["kind"]
    run_id = plan.arguments["run_id"]
    storage_root = Path(plan.storage_root)
    output = plan.arguments.get("output")

    try:
        if kind == "predictive":
            result = render_predictive_research_report(
                RenderPredictiveReportRequest(
                    run_ref=PredictiveRunRef(run_id=run_id),
                    storage_root=storage_root,
                    output_path=Path(output) if output else None,
                )
            )
            return {"run_id": result.run_id, "output_path": str(result.output_path)}

        view_model = build_strategy_dashboard_view_model(
            BuildStrategyDashboardRequest(
                run_ref=StrategyResearchRunRef(run_id=run_id),
                storage_root=storage_root,
            )
        )
        output_path = Path(output) if output else _default_strategy_output(storage_root, run_id)
        written = render_strategy_research_dashboard(view_model, output_path)
        return {
            "run_id": run_id,
            "output_path": str(written),
            "trade_count": view_model.overview.trade_count,
        }
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        raise WorkflowError(f"'report render {kind}' failed: {exc}") from exc


def _default_strategy_output(storage_root: Path | str, run_id: str) -> Path:
    return Path(storage_root) / "reports" / "strategy" / f"{run_id}.html"
