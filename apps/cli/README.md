# trading-cli

Operator CLI for the trading research framework (ADR-0026, Phase 11).

One front door over the workflows already exposed by
`trading_framework.application.*`: `data fetch`, `research run`,
`dry-run start`, `report render`, driven by a single YAML config. It adds no
new capability -- every command calls a workflow that already exists.

## Run locally

```powershell
cd <repo-root>
uv sync --all-packages
uv run trading-cli --help
uv run trading-cli research run --config configs/my_study.yaml --dry-run
```

## Layout

```text
apps/cli/
  pyproject.toml
  src/trading_cli/
    __main__.py       console-script entry point
    cli.py             argparse tree + dispatch
    config.py          YAML config loader + strict validation
    plan.py            resolved-plan model, --dry-run / --json rendering
    errors.py          exit-code taxonomy (0 / 1 / 2)
    commands/          one module per command group
  examples/            one example config per command group (S046-T011)
  tests/
```

See `docs/reference/OPERATOR_CLI.md` for the full operator guide (config
schema, all four command groups, exit codes, known limitations) and
`apps/cli/examples/` for a runnable `--config` starting point per group.

## Boundary

`apps/cli` may import `trading_framework.application.*` only -- never
`trading_framework.research.*`, `.market_analysis.*`, `.strategy.*`,
`.execution.*`, or an infrastructure adapter directly. See
`apps/cli/CLAUDE.md` (added in Wave 3, S046-T013) and ADR-0026 for the full
rule; this differs from `apps/dashboard`, which may not import
`trading_framework` at all.
