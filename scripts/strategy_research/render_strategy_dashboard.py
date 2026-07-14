"""Render a Strategy Research dashboard HTML report from a persisted run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from trading_framework.application.strategy_research import (
    BuildStrategyDashboardRequest,
    build_strategy_dashboard_view_model,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.strategy_dashboard_report import (
    render_strategy_research_dashboard,
)
from trading_framework.research.datasets.strategy_research import StrategyResearchRunRef


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a Strategy Research dashboard HTML report.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Framework storage root containing strategy_research runs",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Persisted Strategy Research run id",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output HTML path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Build the dashboard view model and write standalone HTML."""
    args = _build_parser().parse_args(argv)

    try:
        view_model = build_strategy_dashboard_view_model(
            BuildStrategyDashboardRequest(
                run_ref=StrategyResearchRunRef(run_id=args.run_id),
                storage_root=args.storage_root,
            )
        )
        output_path = render_strategy_research_dashboard(view_model, args.output)
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote dashboard report: {output_path}")
    print(f"trade_count: {view_model.overview.trade_count}")
    print(f"bar_count: {view_model.metadata.bar_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
