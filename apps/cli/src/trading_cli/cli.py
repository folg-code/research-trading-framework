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
4. otherwise calls the command's application-layer body, which currently
   (Wave 1) always raises `NotImplementedCommandError` (exit code 1).

`argparse` itself calls `sys.exit(2)` on a bad/missing flag, which already
matches the "configuration/usage error" exit code -- no translation needed
for the CLI's own parser (only a later `main(argv)` fallback over an existing
script needs `SystemExit` translated, D-S046-09).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import ModuleType

from trading_cli.commands import data, dry_run, report, research
from trading_cli.config import load_config
from trading_cli.errors import EXIT_SUCCESS, CliError
from trading_cli.plan import ResolvedPlan, dump_json, render_plan_json, render_plan_text

_PROG = "trading-cli"

_HANDLERS: dict[tuple[str, str], ModuleType] = {
    ("data", "fetch"): data,
    ("research", "run"): research,
    ("dry-run", "start"): dry_run,
    ("report", "render"): report,
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
    data_commands.add_parser("fetch", parents=[common], help="fetch or import a dataset")

    research_parser = groups.add_parser("research", help="run predictive or strategy research")
    research_commands = research_parser.add_subparsers(
        dest="command", required=True, metavar="{run}"
    )
    research_commands.add_parser("run", parents=[common], help="run a research workflow")

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
    handler = _HANDLERS[(args.group, args.command)]

    config = load_config(args.config)
    plan = handler.resolve_plan(config)

    if args.dry_run:
        _print_plan(plan, json_mode=args.json)
        return EXIT_SUCCESS

    handler.run(plan)
    return EXIT_SUCCESS


def _print_plan(plan: ResolvedPlan, *, json_mode: bool) -> None:
    if json_mode:
        payload = {"status": "dry_run", "plan": render_plan_json(plan)}
        print(dump_json(payload))
    else:
        print(render_plan_text(plan))


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
