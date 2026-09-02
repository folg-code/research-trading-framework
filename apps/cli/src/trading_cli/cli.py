"""Argument parsing and dispatch for `trading-cli` (D-S046-04, D-S046-09, D-S046-10).

Command tree::

    trading-cli data fetch     --config PATH [--dry-run] [--json] [--verbose]
    trading-cli research run   --config PATH [--dry-run] [--json] [--verbose]
    trading-cli dry-run start  --config PATH [--dry-run] [--json] [--verbose]
    trading-cli report render  --config PATH [--dry-run] [--json] [--verbose]

Every command:

1. loads and validates `--config` (a `ConfigError` here is exit code 2),
2. resolves a `ResolvedPlan` from the config alone -- no side effect,
3. if `--dry-run`, prints the plan and exits 0 -- nothing is touched,
4. otherwise calls the command's application-layer body and prints the
   typed result payload it returns (`--json` for machine-readable output).

`argparse` itself calls `sys.exit(2)` on a bad/missing flag, which already
matches the "configuration/usage error" exit code -- no translation needed
for the CLI's own parser (only a later `main(argv)` fallback over an existing
script needs `SystemExit` translated, D-S046-09).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from trading_cli.commands import data, dry_run, report, research
from trading_cli.config import CliConfig, load_config
from trading_cli.errors import EXIT_SUCCESS, CliError
from trading_cli.plan import ResolvedPlan, dump_json, render_plan_json, render_plan_text

_PROG = "trading-cli"

_Handler = tuple[
    Callable[[CliConfig], ResolvedPlan],
    Callable[[ResolvedPlan], dict[str, Any]],
]

_HANDLERS: dict[tuple[str, str], _Handler] = {
    ("data", "fetch"): (data.resolve_plan, data.run),
    ("research", "run"): (research.resolve_plan, research.run),
    ("research", "promote"): (research.resolve_promote_plan, research.run_promote),
    ("dry-run", "start"): (dry_run.resolve_plan, dry_run.run),
    ("report", "render"): (report.resolve_plan, report.run),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_PROG,
        description="Operator CLI for the trading research framework.",
    )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config",
        required=True,
        type=Path,
        metavar="PATH",
        help="path to the trading-cli YAML config (required)",
    )
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve and print the plan; touch nothing on disk",
    )
    common.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output",
    )
    common.add_argument(
        "--verbose",
        action="store_true",
        help="print diagnostics",
    )

    groups = parser.add_subparsers(
        dest="group", required=True, metavar="{data,research,dry-run,report}"
    )

    data_parser = groups.add_parser("data", help="fetch/import market data")
    data_commands = data_parser.add_subparsers(dest="command", required=True, metavar="{fetch}")
    data_commands.add_parser(
        "fetch",
        parents=[common],
        help="fetch or import a dataset",
        description=(
            "Fetch or import a dataset, selected by 'data.provider' in --config.\n\n"
            "'databento' is a local archive IMPORT, not a network fetch: it reads a "
            "'.dbn'/'.dbn.zst' file already on disk (config key 'data.databento.archive') "
            "and publishes a DatasetRef from it. 'binance' (once wired) fetches over the "
            "network for a start/end date range instead -- the two providers have "
            "different config shapes for that reason, not by oversight."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    research_parser = groups.add_parser("research", help="run predictive or strategy research")
    research_commands = research_parser.add_subparsers(
        dest="command", required=True, metavar="{run,promote}"
    )
    research_commands.add_parser(
        "run",
        parents=[common],
        help="run a research workflow",
        description=(
            "Run Predictive or Strategy Research, selected by 'research.kind' in "
            "--config.\n\n"
            "'predictive' is composed: build dataset -> run -> render report, in one "
            "call, with identifiers passed as typed values between steps.\n\n"
            "'strategy' runs a single Strategy Research simulation on a published "
            "DatasetRef, using either the canonical example strategy or an "
            "operator-authored one selected via 'research.strategy.strategy_file' "
            "(a path to a Python file with a zero-argument build_strategy() "
            "function). TRUST MODEL: a strategy_file is loaded and executed with "
            "no sandbox and no import restriction -- the same blast radius as "
            "running that file directly with 'uv run python <file>'. KNOWN "
            "LIMITATION: the simulation assumptions and session resolver remain "
            "hardcoded (same as scripts/strategy_research/run_strategy_research.py). "
            "See docs/reference/OPERATOR_CLI.md (Sprint 047 adds a strategy-authoring guide)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    research_commands.add_parser(
        "promote",
        parents=[common],
        help="promote an existing Predictive Research run into a promoted artifact",
        description=(
            "Promote the last walk-forward fold of an existing Predictive Research "
            "run ('research.promote.run_id' in --config) into a content-addressed "
            "promoted artifact under research/predictive_research/promoted/ "
            "(ADR-0029). Refuses a tree/neural model family or a promotion-time "
            "scikit-learn version mismatch and writes nothing on refusal. Requires "
            "the 'ml' extra (reads the run's fitted joblib blob once)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    dry_run_parser = groups.add_parser("dry-run", help="the BTC futures paper dry-run runtime")
    dry_run_commands = dry_run_parser.add_subparsers(
        dest="command", required=True, metavar="{start}"
    )
    dry_run_commands.add_parser("start", parents=[common], help="start a bounded dry-run")

    report_parser = groups.add_parser("report", help="render an offline HTML report")
    report_commands = report_parser.add_subparsers(
        dest="command", required=True, metavar="{render}"
    )
    report_commands.add_parser("render", parents=[common], help="render a report")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)  # argparse exits 2 itself on a bad/missing flag

    json_mode = bool(getattr(args, "json", False))
    try:
        return _dispatch(args)
    except CliError as exc:
        _print_error(exc, json_mode=json_mode)
        return exc.exit_code


def _dispatch(args: argparse.Namespace) -> int:
    resolve_plan_fn, run_fn = _HANDLERS[(args.group, args.command)]

    config = load_config(args.config)
    plan = resolve_plan_fn(config)

    if args.dry_run:
        _print_plan(plan, json_mode=args.json)
        return EXIT_SUCCESS

    result = run_fn(plan)
    _print_result(result, json_mode=args.json)
    return EXIT_SUCCESS


def _print_plan(plan: ResolvedPlan, *, json_mode: bool) -> None:
    if json_mode:
        payload = {"status": "dry_run", "plan": render_plan_json(plan)}
        print(dump_json(payload))
    else:
        print(render_plan_text(plan))


def _print_result(result: dict[str, Any], *, json_mode: bool) -> None:
    if json_mode:
        print(dump_json({"status": "success", "result": result}))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")


def _print_error(exc: CliError, *, json_mode: bool) -> None:
    if json_mode:
        payload = {
            "status": "error",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "exit_code": exc.exit_code,
        }
        print(dump_json(payload), file=sys.stderr)
    else:
        print(f"error: {exc}", file=sys.stderr)
