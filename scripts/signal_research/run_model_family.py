"""Run a bounded model-family Signal Research experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_framework.application.signal_research.run_signal_research_family import (
    RunSignalResearchFamilyRequest,
    run_signal_research_family_experiment,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import signal_research_family_experiment_dir
from trading_framework.research.reporting.signal_research.family_report_html import (
    render_model_family_comparison_html,
)
from trading_framework.research.signal_research.loader import load_signal_research_definition
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a bounded model-family Signal Research experiment.",
    )
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--definition", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional HTML comparison report path",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print experiment summary as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spec = load_signal_research_definition(args.definition)
        result = run_signal_research_family_experiment(
            RunSignalResearchFamilyRequest(
                spec=spec,
                storage_root=args.storage_root,
                session_resolver=CmeEsRthSessionResolver(),
            )
        )
        report_path = None
        if args.output is not None and result.manifest is not None:
            report_path = render_model_family_comparison_html(
                manifest=result.manifest,
                family_comparison=result.family_comparison,
                output_path=args.output,
            )
        elif result.manifest is not None:
            default_output = (
                signal_research_family_experiment_dir(
                    args.storage_root,
                    result.experiment_id,
                )
                / "family_comparison.html"
            )
            report_path = render_model_family_comparison_html(
                manifest=result.manifest,
                family_comparison=result.family_comparison,
                output_path=default_output,
            )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "experiment_id": result.experiment_id,
        "candidates_generated": result.plan.candidates_generated,
        "candidates_evaluated": result.plan.candidates_evaluated,
        "candidates_skipped": result.plan.candidates_skipped,
        "skipped_variant_ids": list(result.plan.skipped_variant_ids),
        "variant_runs": [
            {"variant_id": item.variant_id, "run_id": item.run_id}
            for item in result.variant_results
        ],
        "comparison_report_path": str(report_path) if report_path is not None else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"experiment_id: {payload['experiment_id']}")
        print(f"candidates_evaluated: {payload['candidates_evaluated']}")
        print(f"candidates_skipped: {payload['candidates_skipped']}")
        if report_path is not None:
            print(f"comparison_report_path: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
